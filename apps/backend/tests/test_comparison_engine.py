from app.models.analysis import SingleGraphAnalysis, ValuePoint
from app.services.comparison_engine import compare_graph_analyses


def _analysis_a() -> SingleGraphAnalysis:
    return SingleGraphAnalysis(
        graph_type="Bar Chart",
        title="A",
        x_axis_label="Quarter",
        y_axis_label="Revenue",
        units="USD",
        categories_or_legends=["Q1", "Q2", "Q3", "Q4"],
        highest_value=ValuePoint(label="Q4", value=100, unit="USD", confidence="high"),
        lowest_value=ValuePoint(label="Q1", value=40, unit="USD", confidence="high"),
        maximum_trend="Increasing",
        minimum_trend="Stable",
    )


def _analysis_b() -> SingleGraphAnalysis:
    return SingleGraphAnalysis(
        graph_type="Bar Chart",
        title="B",
        x_axis_label="Quarter",
        y_axis_label="Revenue",
        units="USD",
        categories_or_legends=["Q1", "Q2", "Q3", "Q4"],
        highest_value=ValuePoint(label="Q4", value=120, unit="USD", confidence="high"),
        lowest_value=ValuePoint(label="Q1", value=50, unit="USD", confidence="high"),
        maximum_trend="Increasing",
        minimum_trend="Stable",
    )


def test_compare_graph_analyses_computes_numeric_changes() -> None:
    result = compare_graph_analyses(_analysis_a(), _analysis_b())

    assert result.comparability.numerically_comparable is True
    assert result.value_comparison[0].absolute_change == 20
    assert result.value_comparison[0].percent_change == 20
    assert len(result.similarities) > 0
