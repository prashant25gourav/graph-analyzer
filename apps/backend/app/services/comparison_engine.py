import json
from typing import Any

from app.models.analysis import SingleGraphAnalysis
from app.models.comparison import (
    Comparability,
    ComparisonInterpretation,
    DeltaValue,
    GraphComparisonResult,
)


def _is_not_available(value: str) -> bool:
    return value.strip().lower() == "not available"


def _compute_delta(label: str, a: float | None, b: float | None, unit: str) -> DeltaValue:
    if a is None or b is None:
        return DeltaValue(label=label, graph_a=a, graph_b=b, unit=unit)

    absolute_change = b - a
    percent_change = None if a == 0 else (absolute_change / a) * 100

    return DeltaValue(
        label=label,
        graph_a=a,
        graph_b=b,
        absolute_change=round(absolute_change, 4),
        percent_change=None if percent_change is None else round(percent_change, 4),
        unit=unit,
    )


def compare_graph_analyses(graph_a: SingleGraphAnalysis, graph_b: SingleGraphAnalysis) -> GraphComparisonResult:
    reasons: list[str] = []
    similarities: list[str] = []
    differences: list[str] = []
    trend_comparison: list[str] = []
    significant_changes: list[str] = []
    uncertainty_notes: list[str] = []

    if graph_a.graph_type == graph_b.graph_type and not _is_not_available(graph_a.graph_type):
        similarities.append(f"Both graphs are {graph_a.graph_type}.")
    else:
        differences.append(f"Graph types differ: {graph_a.graph_type} vs {graph_b.graph_type}.")
        reasons.append("Graph types differ, reducing direct structural comparability.")

    if graph_a.x_axis_label == graph_b.x_axis_label and not _is_not_available(graph_a.x_axis_label):
        similarities.append(f"Both graphs use the same X-axis label: {graph_a.x_axis_label}.")
    else:
        differences.append(f"X-axis differs: {graph_a.x_axis_label} vs {graph_b.x_axis_label}.")

    if graph_a.y_axis_label == graph_b.y_axis_label and not _is_not_available(graph_a.y_axis_label):
        similarities.append(f"Both graphs use the same Y-axis label: {graph_a.y_axis_label}.")
    else:
        differences.append(f"Y-axis differs: {graph_a.y_axis_label} vs {graph_b.y_axis_label}.")

    units_match = graph_a.units == graph_b.units and not _is_not_available(graph_a.units)
    if units_match:
        similarities.append(f"Both graphs use the same units: {graph_a.units}.")
    else:
        differences.append(f"Units differ: {graph_a.units} vs {graph_b.units}.")
        reasons.append("Units differ or are unavailable, limiting numeric comparability.")

    shared_categories = sorted(set(graph_a.categories_or_legends) & set(graph_b.categories_or_legends))
    if shared_categories:
        similarities.append("Shared categories/legends: " + ", ".join(shared_categories) + ".")
    else:
        reasons.append("No overlapping categories or legends were detected.")

    highest_delta = _compute_delta(
        "Highest value",
        graph_a.highest_value.value,
        graph_b.highest_value.value,
        graph_a.highest_value.unit if units_match else "Not Available",
    )
    lowest_delta = _compute_delta(
        "Lowest value",
        graph_a.lowest_value.value,
        graph_b.lowest_value.value,
        graph_a.lowest_value.unit if units_match else "Not Available",
    )

    value_comparison = [highest_delta, lowest_delta]

    if highest_delta.absolute_change is not None:
        direction = "increased" if highest_delta.absolute_change > 0 else "decreased"
        trend_comparison.append(f"Highest value {direction} by {abs(highest_delta.absolute_change):.2f}.")
        if highest_delta.percent_change is not None and abs(highest_delta.percent_change) >= 10:
            significant_changes.append(
                f"Highest value changed by {highest_delta.percent_change:.2f}% between Graph A and Graph B."
            )
    else:
        uncertainty_notes.append("Highest value change could not be computed due to missing numeric data.")

    if lowest_delta.absolute_change is not None:
        direction = "increased" if lowest_delta.absolute_change > 0 else "decreased"
        trend_comparison.append(f"Lowest value {direction} by {abs(lowest_delta.absolute_change):.2f}.")
    else:
        uncertainty_notes.append("Lowest value change could not be computed due to missing numeric data.")

    if graph_a.maximum_trend == graph_b.maximum_trend and not _is_not_available(graph_a.maximum_trend):
        similarities.append(f"Maximum trend is similar: {graph_a.maximum_trend}.")
    else:
        trend_comparison.append(
            f"Maximum trend differs: {graph_a.maximum_trend} vs {graph_b.maximum_trend}."
        )

    if graph_a.minimum_trend == graph_b.minimum_trend and not _is_not_available(graph_a.minimum_trend):
        similarities.append(f"Minimum trend is similar: {graph_a.minimum_trend}.")
    else:
        trend_comparison.append(
            f"Minimum trend differs: {graph_a.minimum_trend} vs {graph_b.minimum_trend}."
        )

    structurally_comparable = len(reasons) < 3
    numerically_comparable = units_match and highest_delta.absolute_change is not None and lowest_delta.absolute_change is not None

    if not reasons:
        reasons.append("Graphs are largely comparable using available structure and metrics.")


    return GraphComparisonResult(
        graph_a=graph_a,
        graph_b=graph_b,
        comparability=Comparability(
            structurally_comparable=structurally_comparable,
            numerically_comparable=numerically_comparable,
            reasons=reasons,
        ),
        similarities=similarities,
        differences=differences,
        value_comparison=value_comparison,
        trend_comparison=trend_comparison,
        significant_changes=significant_changes,
        uncertainty_notes=uncertainty_notes,
    )


def _value_summary(point_label: str, value: float | None, unit: str) -> str:
    if value is None:
        return f"{point_label}: Not Available"
    unit_text = "" if _is_not_available(unit) else f" {unit}"
    return f"{point_label}: {value}{unit_text}"


def build_comparison_prompt(result: GraphComparisonResult) -> str:
    """Build a text-only prompt from the structured comparison result.

    We deliberately reuse the structured single-graph analyses and the
    deterministic comparison facts instead of re-sending the raw images. The
    model is asked only to interpret; all numbers come from code.
    """
    a = result.graph_a
    b = result.graph_b

    facts: dict[str, Any] = {
        "graph_a": {
            "graph_type": a.graph_type,
            "title": a.title,
            "x_axis_label": a.x_axis_label,
            "y_axis_label": a.y_axis_label,
            "units": a.units,
            "categories_or_legends": a.categories_or_legends,
            "highest_value": _value_summary("highest", a.highest_value.value, a.highest_value.unit),
            "lowest_value": _value_summary("lowest", a.lowest_value.value, a.lowest_value.unit),
            "maximum_trend": a.maximum_trend,
            "minimum_trend": a.minimum_trend,
        },
        "graph_b": {
            "graph_type": b.graph_type,
            "title": b.title,
            "x_axis_label": b.x_axis_label,
            "y_axis_label": b.y_axis_label,
            "units": b.units,
            "categories_or_legends": b.categories_or_legends,
            "highest_value": _value_summary("highest", b.highest_value.value, b.highest_value.unit),
            "lowest_value": _value_summary("lowest", b.lowest_value.value, b.lowest_value.unit),
            "maximum_trend": b.maximum_trend,
            "minimum_trend": b.minimum_trend,
        },
        "computed_value_changes": [
            {
                "label": d.label,
                "graph_a": d.graph_a,
                "graph_b": d.graph_b,
                "absolute_change": d.absolute_change,
                "percent_change": d.percent_change,
                "unit": d.unit,
            }
            for d in result.value_comparison
        ],
        "comparability": {
            "structurally_comparable": result.comparability.structurally_comparable,
            "numerically_comparable": result.comparability.numerically_comparable,
            "reasons": result.comparability.reasons,
        },
        "deterministic_similarities": result.similarities,
        "deterministic_differences": result.differences,
        "deterministic_trend_comparison": result.trend_comparison,
        "deterministic_significant_changes": result.significant_changes,
    }

    return (
        "You are an expert data analyst comparing two graphs. "
        "You are given structured, already-extracted facts about Graph A and Graph B, "
        "plus deterministic value changes computed by trusted code. "
        "Interpret these facts. Do NOT invent numbers or recompute values; rely only on the provided data. "
        "If the graphs are not meaningfully comparable (different units, unrelated metrics, "
        "incompatible categories, or insufficient information), say so explicitly and do NOT fabricate "
        "numeric comparisons. "
        "Return ONLY valid JSON, no markdown and no prose outside JSON, using exactly these keys: "
        "{"
        '"comparative_insights": string[], '
        '"recommendations": string[], '
        '"summary": string'
        "}. "
        "Provide exactly 3 comparative_insights and exactly 3 recommendations. "
        "The summary should be a concise 80-150 word paragraph grounded in the provided facts. "
        "Here are the facts as JSON:\n"
        f"{json.dumps(facts, ensure_ascii=False)}"
    )


def normalize_comparison_interpretation(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw LLM payload into the ComparisonInterpretation shape.

    Missing fields, wrong types, and empty arrays are handled gracefully so a
    single bad field never crashes the request.
    """

    def _str_list(key: str, expected_count: int) -> list[str]:
        raw = payload.get(key, [])
        items: list[str] = []
        if isinstance(raw, list):
            for value in raw:
                text = str(value).strip() if value is not None else ""
                if text:
                    items.append(text)
        normalized = items[:expected_count]
        while len(normalized) < expected_count:
            normalized.append("Not Available")
        return normalized

    summary_raw = payload.get("summary")
    summary = str(summary_raw).strip() if summary_raw is not None else ""

    return {
        "comparative_insights": _str_list("comparative_insights", 3),
        "recommendations": _str_list("recommendations", 3),
        "summary": summary or "Not Available",
    }


def build_fallback_interpretation(result: GraphComparisonResult) -> ComparisonInterpretation:
    """Deterministic, honest interpretation used when the LLM is unavailable.

    This is derived entirely from the computed comparison, so it is dynamic
    (varies with the actual graphs) and never fabricates data.
    """
    a_title = result.graph_a.title if not _is_not_available(result.graph_a.title) else "Graph A"
    b_title = result.graph_b.title if not _is_not_available(result.graph_b.title) else "Graph B"

    comparable = result.comparability.numerically_comparable
    highest = next((d for d in result.value_comparison if d.label == "Highest value"), None)

    insights: list[str] = []
    if result.significant_changes:
        insights.extend(result.significant_changes)
    if result.differences:
        insights.append(result.differences[0])
    if result.similarities:
        insights.append(result.similarities[0])
    if not comparable:
        insights.append(
            "The graphs are only partially comparable, so numeric conclusions should be treated with caution: "
            + "; ".join(result.comparability.reasons)
        )
    while len(insights) < 3:
        insights.append("Not Available")
    insights = insights[:3]

    recommendations: list[str] = []
    if not comparable:
        recommendations.append(
            "Align units and category labels across both graphs before drawing numeric conclusions."
        )
    if highest is not None and highest.percent_change is not None:
        recommendations.append(
            f"Investigate the drivers behind the {highest.percent_change:.1f}% change in the highest value."
        )
    recommendations.append(
        "Confirm that both graphs cover matching periods or categories before making business decisions."
    )
    while len(recommendations) < 3:
        recommendations.append("Not Available")
    recommendations = recommendations[:3]

    parts: list[str] = [f"Comparison of {a_title} and {b_title}."]
    if highest is not None and highest.absolute_change is not None:
        direction = "increased" if highest.absolute_change > 0 else "decreased"
        pct = "" if highest.percent_change is None else f" ({highest.percent_change:.1f}%)"
        parts.append(
            f"The highest value {direction} by {abs(highest.absolute_change):.2f}{pct} from Graph A to Graph B."
        )
    else:
        parts.append("Numeric values were insufficient to compute a reliable value change.")
    if comparable:
        parts.append("Units and values align, so the numeric comparison above is reliable.")
    else:
        parts.append(
            "The graphs are only partially comparable, so differences in structure or units are highlighted "
            "instead of forcing a numeric comparison."
        )
    parts.append("(AI interpretation was unavailable; this summary was generated deterministically from the computed comparison.)")
    summary = " ".join(parts)

    return ComparisonInterpretation(
        comparative_insights=insights,
        recommendations=recommendations,
        summary=summary,
    )

