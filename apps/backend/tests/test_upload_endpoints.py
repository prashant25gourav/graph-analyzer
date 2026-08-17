from contextlib import contextmanager
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import app
from app.models.analysis import SingleGraphAnalysis
from app.models.comparison import ComparisonInterpretation
from app.services.comparison_engine import normalize_comparison_interpretation
from app.services.groq_graph_service import AIServiceError, get_graph_service


class _FakeGraphService:
    """Deterministic stand-in for the Groq-backed service.

    Mirrors the real service's public surface used by the routes:
    ``analyze_graph`` and ``interpret_comparison``. No network calls.
    """

    def analyze_graph(self, validated_image) -> SingleGraphAnalysis:  # noqa: ANN001
        if validated_image.filename.lower().startswith("b"):
            highest_value = {"label": "Q4", "value": 120.0, "unit": "USD", "confidence": "high"}
            lowest_value = {"label": "Q1", "value": 50.0, "unit": "USD", "confidence": "high"}
            title = "Synthetic Test Chart B"
        else:
            highest_value = {"label": "Q4", "value": 100.0, "unit": "USD", "confidence": "high"}
            lowest_value = {"label": "Q1", "value": 40.0, "unit": "USD", "confidence": "high"}
            title = "Synthetic Test Chart A"

        return SingleGraphAnalysis(
            graph_type="Bar Chart",
            title=title,
            x_axis_label="Quarter",
            y_axis_label="Revenue",
            units="USD",
            categories_or_legends=["Q1", "Q2", "Q3", "Q4"],
            highest_value=highest_value,
            lowest_value=lowest_value,
            observations=[
                "Observation 1",
                "Observation 2",
                "Observation 3",
                "Observation 4",
                "Observation 5",
            ],
            business_insights=["Insight 1", "Insight 2", "Insight 3"],
            recommendations=["Recommendation 1", "Recommendation 2", "Recommendation 3"],
            summary="This is a deterministic test summary.",
        )

    def interpret_comparison(self, comparison) -> ComparisonInterpretation:  # noqa: ANN001
        return ComparisonInterpretation(
            comparative_insights=[
                "Insight about the two graphs.",
                "Second comparative insight.",
                "Third comparative insight.",
            ],
            recommendations=[
                "First recommendation.",
                "Second recommendation.",
                "Third recommendation.",
            ],
            summary="Deterministic interpretation summary for tests.",
        )


class _IncomparableGraphService(_FakeGraphService):
    """Returns two graphs with different units so they are not numerically comparable."""

    def analyze_graph(self, validated_image) -> SingleGraphAnalysis:  # noqa: ANN001
        if validated_image.filename.lower().startswith("b"):
            return SingleGraphAnalysis(
                graph_type="Pie Chart",
                title="Market Share",
                x_axis_label="Not Available",
                y_axis_label="Not Available",
                units="percent",
                categories_or_legends=["A", "B"],
                highest_value={"label": "A", "value": 60.0, "unit": "percent", "confidence": "low"},
                lowest_value={"label": "B", "value": 40.0, "unit": "percent", "confidence": "low"},
            )
        return SingleGraphAnalysis(
            graph_type="Line Chart",
            title="Latency",
            x_axis_label="Day",
            y_axis_label="ms",
            units="ms",
            categories_or_legends=["Mon", "Tue"],
            highest_value={"label": "Mon", "value": 300.0, "unit": "ms", "confidence": "medium"},
            lowest_value={"label": "Tue", "value": 100.0, "unit": "ms", "confidence": "medium"},
        )


class _AIFailingAnalyzeService(_FakeGraphService):
    def analyze_graph(self, validated_image):  # noqa: ANN001, ANN201
        raise AIServiceError(502, "groq_unavailable", "The AI service is temporarily unavailable.")


class _InterpretFailingService(_FakeGraphService):
    """analyze works, but interpretation fails -> route must use deterministic fallback."""

    def interpret_comparison(self, comparison):  # noqa: ANN001, ANN201
        raise AIServiceError(504, "groq_timeout", "The AI service timed out.")


class _CrashingService(_FakeGraphService):
    def analyze_graph(self, validated_image):  # noqa: ANN001, ANN201
        raise RuntimeError("secret internal detail that must not leak to clients")


app.dependency_overrides[get_graph_service] = lambda: _FakeGraphService()

# Default client re-raises server exceptions so real bugs surface in tests.
client = TestClient(app)
handled_client = TestClient(app, raise_server_exceptions=False)


@contextmanager
def _use_service(service):
    """Temporarily swap the graph service dependency, then restore the default."""
    previous = app.dependency_overrides.get(get_graph_service)
    app.dependency_overrides[get_graph_service] = lambda: service
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_graph_service] = previous


def _make_png_bytes() -> bytes:
    image = Image.new("RGB", (40, 40), color=(0, 128, 128))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()




def test_health_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "graph-analyzer-api"




def test_analyze_accepts_valid_png() -> None:
    png_bytes = _make_png_bytes()

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("chart.png", png_bytes, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["workflow"] == "single_analysis"
    assert body["analysis"]["graph_type"] == "Bar Chart"


def test_analyze_rejects_unsupported_type() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("chart.gif", b"GIF89a", "image/gif")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["error_code"] == "unsupported_image_type"


def test_analyze_rejects_malformed_image() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("broken.png", b"not-a-real-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "malformed_image"


def test_analyze_rejects_oversized_image() -> None:
    settings = get_settings()
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (settings.max_upload_mb * 1024 * 1024 + 1024)

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("huge.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "file_too_large"


def test_analyze_ai_failure_is_sanitized() -> None:
    png_bytes = _make_png_bytes()

    with _use_service(_AIFailingAnalyzeService()):
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("chart.png", png_bytes, "image/png")},
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["error_code"] == "groq_unavailable"
    # The client-facing message must not contain internal exception text.
    assert "Traceback" not in response.text
    assert "secret internal detail" not in response.text


def test_unhandled_exception_returns_generic_message() -> None:
    png_bytes = _make_png_bytes()

    with _use_service(_CrashingService()):
        response = handled_client.post(
            "/api/v1/analyze",
            files={"file": ("chart.png", png_bytes, "image/png")},
        )

    assert response.status_code == 500
    body = response.json()
    assert body["message"] == "An internal server error occurred."
    assert body["error_code"] == "internal_error"
    # No leak of the internal RuntimeError text or a stack trace.
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text




def test_compare_accepts_two_valid_png_files() -> None:
    png_a = _make_png_bytes()
    png_b = _make_png_bytes()

    response = client.post(
        "/api/v1/compare",
        files={
            "graph_a": ("a.png", png_a, "image/png"),
            "graph_b": ("b.png", png_b, "image/png"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["workflow"] == "graph_comparison"
    assert body["graph_a"]["analysis"]["title"] == "Synthetic Test Chart A"
    assert body["graph_b"]["analysis"]["title"] == "Synthetic Test Chart B"
    assert "comparison" in body
    assert body["comparison"]["comparability"]["numerically_comparable"] is True


def test_compare_returns_dynamic_interpretation_prose() -> None:
    png_a = _make_png_bytes()
    png_b = _make_png_bytes()

    response = client.post(
        "/api/v1/compare",
        files={
            "graph_a": ("a.png", png_a, "image/png"),
            "graph_b": ("b.png", png_b, "image/png"),
        },
    )

    assert response.status_code == 200
    comparison = response.json()["comparison"]
    # Deterministic deltas are real: 120 vs 100 highest -> +20 / +20%.
    assert comparison["value_comparison"][0]["absolute_change"] == 20.0
    # Interpretation prose is populated (not the "Not Available" placeholder).
    assert comparison["summary"] != "Not Available"
    assert len(comparison["comparative_insights"]) == 3
    assert len(comparison["recommendations"]) == 3


def test_compare_uses_fallback_when_interpretation_fails() -> None:
    png_a = _make_png_bytes()
    png_b = _make_png_bytes()

    with _use_service(_InterpretFailingService()):
        response = client.post(
            "/api/v1/compare",
            files={
                "graph_a": ("a.png", png_a, "image/png"),
                "graph_b": ("b.png", png_b, "image/png"),
            },
        )

    assert response.status_code == 200
    comparison = response.json()["comparison"]
    # Deterministic fallback still produces usable prose and flags the degradation.
    assert comparison["summary"] != "Not Available"
    assert len(comparison["comparative_insights"]) == 3
    assert any(
        "AI interpretation was unavailable" in note
        for note in comparison["uncertainty_notes"]
    )


def test_compare_flags_incomparable_graphs_without_fabricating() -> None:
    png_a = _make_png_bytes()
    png_b = _make_png_bytes()

    with _use_service(_IncomparableGraphService()):
        response = client.post(
            "/api/v1/compare",
            files={
                "graph_a": ("a.png", png_a, "image/png"),
                "graph_b": ("b.png", png_b, "image/png"),
            },
        )

    assert response.status_code == 200
    comparison = response.json()["comparison"]
    assert comparison["comparability"]["numerically_comparable"] is False
    assert len(comparison["comparability"]["reasons"]) > 0
    assert comparison["summary"] != "Not Available"


def test_compare_rejects_invalid_second_image() -> None:
    png_a = _make_png_bytes()

    response = client.post(
        "/api/v1/compare",
        files={
            "graph_a": ("a.png", png_a, "image/png"),
            "graph_b": ("bad.txt", b"hello", "text/plain"),
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"]["error_code"] == "unsupported_image_type"




def test_normalize_interpretation_pads_and_coerces() -> None:
    normalized = normalize_comparison_interpretation(
        {
            "comparative_insights": ["only one"],
            "recommendations": "not a list",  
        }
    )

    assert len(normalized["comparative_insights"]) == 3
    assert len(normalized["recommendations"]) == 3
    assert normalized["summary"] == "Not Available"
    # The normalized payload validates cleanly against the schema.
    model = ComparisonInterpretation.model_validate(normalized)
    assert model.summary == "Not Available"


def test_normalize_interpretation_handles_empty_payload() -> None:
    normalized = normalize_comparison_interpretation({})

    assert normalized["summary"] == "Not Available"
    assert normalized["comparative_insights"] == ["Not Available", "Not Available", "Not Available"]
    assert normalized["recommendations"] == ["Not Available", "Not Available", "Not Available"]
    ComparisonInterpretation.model_validate(normalized)
