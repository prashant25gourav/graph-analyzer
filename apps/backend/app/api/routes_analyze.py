import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.services.groq_graph_service import AIServiceError, GroqGraphService, get_graph_service
from app.utils.image_validation import ImageValidationError, validate_upload_image

logger = logging.getLogger("app.analyze")

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze")
async def analyze_graph(
    file: UploadFile = File(...),
    graph_service: GroqGraphService = Depends(get_graph_service),
) -> dict:
    settings = get_settings()

    try:
        validated_image = await validate_upload_image(file, settings)
    except ImageValidationError as exc:
        logger.info("analyze rejected upload: %s (%s)", exc.error_code, exc.status_code)
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    try:
        # The Groq SDK call is synchronous/blocking; run it in a worker thread
        # so it does not block the event loop (and other requests) on the server.
        analysis = await run_in_threadpool(graph_service.analyze_graph, validated_image)
    except AIServiceError as exc:
        logger.warning(
            "analyze AI failure: %s (%s) file=%s",
            exc.error_code,
            exc.status_code,
            validated_image.filename,
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    return {
        "status": "completed",
        "workflow": "single_analysis",
        "message": "Image validated and analyzed successfully.",
        "file": {
            "filename": validated_image.filename,
            "content_type": validated_image.content_type,
            "size_bytes": validated_image.size_bytes,
            "width": validated_image.width,
            "height": validated_image.height,
            "format": validated_image.image_format,
        },
        "analysis": analysis.model_dump(),
    }
