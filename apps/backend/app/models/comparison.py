from pydantic import BaseModel, Field

from app.models.analysis import SingleGraphAnalysis


class DeltaValue(BaseModel):
    label: str = "Not Available"
    graph_a: float | None = None
    graph_b: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    unit: str = "Not Available"


class Comparability(BaseModel):
    structurally_comparable: bool = False
    numerically_comparable: bool = False
    reasons: list[str] = Field(default_factory=list)


class GraphComparisonResult(BaseModel):
    graph_a: SingleGraphAnalysis
    graph_b: SingleGraphAnalysis
    comparability: Comparability
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    value_comparison: list[DeltaValue] = Field(default_factory=list)
    trend_comparison: list[str] = Field(default_factory=list)
    significant_changes: list[str] = Field(default_factory=list)
    comparative_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = "Not Available"
    uncertainty_notes: list[str] = Field(default_factory=list)


class ComparisonInterpretation(BaseModel):
    comparative_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = "Not Available"
