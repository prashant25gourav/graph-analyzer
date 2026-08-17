from app.services.groq_graph_service import _extract_json_payload, _normalize_single_graph_payload


def test_extract_json_payload_from_fenced_block() -> None:
    raw = """```json
{"graph_type":"Line Chart"}
```"""

    payload = _extract_json_payload(raw)
    assert payload["graph_type"] == "Line Chart"


def test_normalize_single_graph_payload_pads_required_lists() -> None:
    payload = {
        "graph_type": "Line Chart",
        "observations": ["A"],
        "business_insights": [],
        "recommendations": ["R1", "R2"],
    }

    normalized = _normalize_single_graph_payload(payload)
    assert len(normalized["observations"]) == 5
    assert len(normalized["business_insights"]) == 3
    assert len(normalized["recommendations"]) == 3
    assert normalized["recommendations"][2] == "Not Available"
