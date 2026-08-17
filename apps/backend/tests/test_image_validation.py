import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image

from app.core.config import Settings
from app.utils.image_validation import ImageValidationError, validate_upload_image


def _settings(max_upload_mb: int = 1) -> Settings:
    return Settings(
        APP_ENV="test",
        PORT=8000,
        LOG_LEVEL="INFO",
        GROQ_API_KEY="",
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        MAX_UPLOAD_MB=max_upload_mb,
        REQUEST_TIMEOUT_SECONDS=30,
    )


def _png_bytes() -> bytes:
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_validate_upload_image_success() -> None:
    upload = UploadFile(filename="ok.png", file=BytesIO(_png_bytes()), headers={"content-type": "image/png"})
    validated = asyncio.run(validate_upload_image(upload, _settings()))

    assert validated.content_type == "image/png"
    assert validated.width == 16
    assert validated.height == 16


def test_validate_upload_image_oversize_rejected() -> None:
    upload = UploadFile(
        filename="big.png",
        file=BytesIO(b"x" * (2 * 1024 * 1024)),
        headers={"content-type": "image/png"},
    )

    with pytest.raises(ImageValidationError) as exc:
        asyncio.run(validate_upload_image(upload, _settings(max_upload_mb=1)))

    assert exc.value.error_code == "file_too_large"
