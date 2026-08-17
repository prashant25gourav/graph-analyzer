from pydantic import BaseModel, Field


class ValuePoint(BaseModel):
    label: str = "Not Available"
    value: float | None = None
    unit: str = "Not Available"
    confidence: str = "low"


class SingleGraphAnalysis(BaseModel):
    graph_type: str = "Not Available"
    title: str = "Not Available"
    x_axis_label: str = "Not Available"
    y_axis_label: str = "Not Available"
    units: str = "Not Available"
    categories_or_legends: list[str] = Field(default_factory=list)
    highest_value: ValuePoint = Field(default_factory=ValuePoint)
    lowest_value: ValuePoint = Field(default_factory=ValuePoint)
    maximum_trend: str = "Not Available"
    minimum_trend: str = "Not Available"
    observations: list[str] = Field(default_factory=list)
    business_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = "Not Available"
    uncertainty_notes: list[str] = Field(default_factory=list)
