import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_analyze import router as analyze_router
from app.api.routes_compare import router as compare_router
from app.api.routes_health import router as health_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AI Graph Analyzer API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "internal_error",
                "message": "An internal server error occurred.",
            },
        )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "AI Graph Analyzer API is running",
            "docs": "/api/docs",
            "health": "/api/health",
        }

    app.include_router(health_router)
    app.include_router(analyze_router)
    app.include_router(compare_router)

    logger.info(
        "AI Graph Analyzer API initialized (env=%s, model=%s, cors_origins=%d)",
        settings.app_env,
        settings.groq_model,
        len(settings.cors_origins),
    )
    return app


app = create_app()
