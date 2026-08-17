import base64
import json
import logging
import re
from typing import Any

from fastapi import Depends
from groq import Groq

from app.core.config import Settings, get_settings
from app.models.analysis import SingleGraphAnalysis, ValuePoint
from app.models.comparison import ComparisonInterpretation, GraphComparisonResult
from app.services.comparison_engine import (
    build_comparison_prompt,
    normalize_comparison_interpretation,
)
from app.utils.image_validation import ValidatedImage

logger = logging.getLogger("app.groq")


class AIServiceError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str, details: str | None = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


class GroqGraphService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _require_api_key(self) -> None:
        if not self.settings.groq_api_key:
            raise AIServiceError(
                503,
                "missing_groq_api_key",
                "GROQ_API_KEY is not configured on the server.",
            )

    def _map_groq_exception(self, exc: Exception, context: str) -> "AIServiceError":
        """Map a Groq SDK exception to a safe AIServiceError.

        The real exception is logged server-side; the client never receives
        the exception text or a stack trace.
        """
        message = str(exc).lower()
        if "timeout" in message:
            logger.warning("%s: Groq request timed out", context)
            return AIServiceError(504, "groq_timeout", "Groq request timed out.")
        if "api key" in message or "authentication" in message or "unauthorized" in message:
            logger.error("%s: Groq authentication failed", context)
            return AIServiceError(502, "groq_auth_error", "Groq authentication failed.")
        logger.exception("%s: Groq request failed", context)
        return AIServiceError(502, "groq_request_failed", "Groq request failed.")

    def analyze_graph(self, validated_image: ValidatedImage) -> SingleGraphAnalysis:
        self._require_api_key()

        client = Groq(api_key=self.settings.groq_api_key)
        encoded_image = base64.b64encode(validated_image.raw_bytes).decode("utf-8")

        prompt = _single_graph_prompt()

        try:
            response = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{validated_image.content_type};base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                timeout=self.settings.request_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._map_groq_exception(exc, "analyze_graph") from exc

        try:
            content = response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.error("analyze_graph: could not read Groq response content")
            raise AIServiceError(502, "groq_empty_response", "Groq returned an unreadable response.") from exc

        payload = _extract_json_payload(content)
        normalized = _normalize_single_graph_payload(payload)
        return SingleGraphAnalysis.model_validate(normalized)

    def interpret_comparison(self, comparison: GraphComparisonResult) -> ComparisonInterpretation:
        """Generate interpretive prose for a comparison from structured facts.

        This is a text-only Groq call: it reuses the already-extracted
        structured analyses and the deterministic value changes rather than
        re-sending the raw images. The response is validated against the
        ComparisonInterpretation schema; malformed output raises AIServiceError
        so the caller can fall back gracefully.
        """
        self._require_api_key()

        client = Groq(api_key=self.settings.groq_api_key)
        prompt = build_comparison_prompt(comparison)

        try:
            response = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=self.settings.request_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._map_groq_exception(exc, "interpret_comparison") from exc

        try:
            content = response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.error("interpret_comparison: could not read Groq response content")
            raise AIServiceError(502, "groq_empty_response", "Groq returned an unreadable response.") from exc

        payload = _extract_json_payload(content)
        normalized = normalize_comparison_interpretation(payload)
        return ComparisonInterpretation.model_validate(normalized)


def get_graph_service(settings: Settings = Depends(get_settings)) -> GroqGraphService:
    return GroqGraphService(settings)


def _single_graph_prompt() -> str:
    return (
        "You are an expert data analyst specialized in graph understanding. "
        "Analyze the provided graph image and return only valid JSON with no markdown, no prose outside JSON. "
        "Use this exact structure and key names: "
        "{"
        '"graph_type": string, '
        '"title": string, '
        '"x_axis_label": string, '
        '"y_axis_label": string, '
        '"units": string, '
        '"categories_or_legends": string[], '
        '"highest_value": {"label": string, "value": number|null, "unit": string, "confidence": string}, '
        '"lowest_value": {"label": string, "value": number|null, "unit": string, "confidence": string}, '
        '"maximum_trend": string, '
        '"minimum_trend": string, '
        '"observations": string[], '
        '"business_insights": string[], '
        '"recommendations": string[], '
        '"summary": string, '
        '"uncertainty_notes": string[]'
        "}. "
        "Rules: If any field cannot be determined, return 'Not Available'. "
        "Never invent precise numbers when uncertain. Use null for unknown numeric values and add an uncertainty note. "
        "Return exactly 5 observations, 3 business_insights, and 3 recommendations. "
        "Summary should be around 100 to 150 words when possible."
    )


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    stripped = raw_text.strip()
    if not stripped:
        raise AIServiceError(502, "groq_empty_content", "Groq returned empty content.")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    object_match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if object_match:
        candidate = object_match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            logger.warning("Groq response contained an unparseable JSON object: %s", exc)
            raise AIServiceError(
                502,
                "groq_malformed_json",
                "Groq response did not contain valid JSON.",
            ) from exc

    raise AIServiceError(502, "groq_malformed_json", "Groq response did not contain a JSON object.")


def _normalize_single_graph_payload(payload: dict[str, Any]) -> dict[str, Any]:
    def _str(key: str, default: str = "Not Available") -> str:
        value = payload.get(key, default)
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    def _str_list(key: str, expected_count: int | None = None) -> list[str]:
        raw = payload.get(key, [])
        items: list[str] = []
        if isinstance(raw, list):
            for value in raw:
                text = str(value).strip() if value is not None else ""
                if text:
                    items.append(text)
        if expected_count is None:
            return items

        normalized = items[:expected_count]
        while len(normalized) < expected_count:
            normalized.append("Not Available")
        return normalized

    def _value_point(key: str) -> ValuePoint:
        raw = payload.get(key, {})
        if not isinstance(raw, dict):
            raw = {}

        raw_value = raw.get("value")
        value: float | None = None
        if isinstance(raw_value, (int, float)):
            value = float(raw_value)
        elif isinstance(raw_value, str):
            cleaned = re.sub(r"[^0-9.\-]", "", raw_value)
            if cleaned:
                try:
                    value = float(cleaned)
                except ValueError:
                    value = None

        return ValuePoint(
            label=str(raw.get("label") or "Not Available").strip() or "Not Available",
            value=value,
            unit=str(raw.get("unit") or "Not Available").strip() or "Not Available",
            confidence=str(raw.get("confidence") or "low").strip() or "low",
        )

    return {
        "graph_type": _str("graph_type"),
        "title": _str("title"),
        "x_axis_label": _str("x_axis_label"),
        "y_axis_label": _str("y_axis_label"),
        "units": _str("units"),
        "categories_or_legends": _str_list("categories_or_legends"),
        "highest_value": _value_point("highest_value").model_dump(),
        "lowest_value": _value_point("lowest_value").model_dump(),
        "maximum_trend": _str("maximum_trend"),
        "minimum_trend": _str("minimum_trend"),
        "observations": _str_list("observations", expected_count=5),
        "business_insights": _str_list("business_insights", expected_count=3),
        "recommendations": _str_list("recommendations", expected_count=3),
        "summary": _str("summary"),
        "uncertainty_notes": _str_list("uncertainty_notes"),
    }
