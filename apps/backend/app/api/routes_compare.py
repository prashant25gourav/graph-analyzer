import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.services.comparison_engine import build_fallback_interpretation, compare_graph_analyses
from app.services.groq_graph_service import AIServiceError, GroqGraphService, get_graph_service
from app.utils.image_validation import ImageValidationError, validate_upload_image

logger = logging.getLogger("app.compare")

router = APIRouter(prefix="/api/v1", tags=["compare"])


@router.post("/compare")
async def compare_graphs(
    graph_a: UploadFile = File(...),
    graph_b: UploadFile = File(...),
    graph_service: GroqGraphService = Depends(get_graph_service),
) -> dict:
    settings = get_settings()

    try:
        validated_a = await validate_upload_image(graph_a, settings)
        validated_b = await validate_upload_image(graph_b, settings)
    except ImageValidationError as exc:
        logger.info("compare rejected upload: %s (%s)", exc.error_code, exc.status_code)
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    try:
        # Analyze each graph independently. The Groq SDK call is blocking, so
        # run it in a worker thread to keep the event loop responsive.
        analysis_a = await run_in_threadpool(graph_service.analyze_graph, validated_a)
        analysis_b = await run_in_threadpool(graph_service.analyze_graph, validated_b)
    except AIServiceError as exc:
        logger.warning("compare AI extraction failure: %s (%s)", exc.error_code, exc.status_code)
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    # Deterministic structural + numeric comparison (no fabricated numbers).
    comparison = compare_graph_analyses(analysis_a, analysis_b)

    # AI interpretation over the structured facts. If it fails or returns
    # unusable content, fall back to an honest, deterministic interpretation
    # derived from the computed comparison rather than failing the request.
    try:
        interpretation = await run_in_threadpool(graph_service.interpret_comparison, comparison)
    except AIServiceError as exc:
        logger.warning(
            "compare interpretation failed (%s); using deterministic fallback",
            exc.error_code,
        )
        interpretation = build_fallback_interpretation(comparison)
        comparison.uncertainty_notes.append(
            "AI interpretation was unavailable; comparison prose was generated deterministically."
        )

    comparison.comparative_insights = interpretation.comparative_insights
    comparison.recommendations = interpretation.recommendations
    comparison.summary = interpretation.summary

    return {
        "status": "completed",
        "workflow": "graph_comparison",
        "message": "Both images validated, analyzed, and compared successfully.",
        "graph_a": {
            "filename": validated_a.filename,
            "content_type": validated_a.content_type,
            "size_bytes": validated_a.size_bytes,
            "width": validated_a.width,
            "height": validated_a.height,
            "format": validated_a.image_format,
            "analysis": analysis_a.model_dump(),
        },
        "graph_b": {
            "filename": validated_b.filename,
            "content_type": validated_b.content_type,
            "size_bytes": validated_b.size_bytes,
            "width": validated_b.width,
            "height": validated_b.height,
            "format": validated_b.image_format,
            "analysis": analysis_b.model_dump(),
        },
        "comparison": comparison.model_dump(),
    }
