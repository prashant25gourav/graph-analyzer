from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings


ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}


class ImageValidationError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str, details: str | None = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


@dataclass
class ValidatedImage:
    filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    image_format: str
    raw_bytes: bytes


async def validate_upload_image(upload_file: UploadFile, settings: Settings) -> ValidatedImage:
    if not upload_file.filename:
        raise ImageValidationError(400, "missing_filename", "Uploaded file must include a filename.")

    content_type = (upload_file.content_type or "").lower().strip()
    if content_type not in ALLOWED_MIME_TYPES:
        raise ImageValidationError(
            415,
            "unsupported_image_type",
            "Unsupported image type.",
            details=f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    raw_bytes = await upload_file.read()
    if not raw_bytes:
        raise ImageValidationError(400, "empty_file", "Uploaded image is empty.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise ImageValidationError(
            413,
            "file_too_large",
            "Uploaded image exceeds size limit.",
            details=f"Maximum allowed size is {settings.max_upload_mb} MB.",
        )

    try:
        verifier = Image.open(BytesIO(raw_bytes))
        verifier.verify()

        parser = Image.open(BytesIO(raw_bytes))
        width, height = parser.size
        image_format = parser.format or "Unknown"
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError(
            422,
            "malformed_image",
            "Uploaded file is not a valid image or is corrupted.",
        ) from exc

    return ValidatedImage(
        filename=upload_file.filename,
        content_type=content_type,
        size_bytes=len(raw_bytes),
        width=width,
        height=height,
        image_format=image_format,
        raw_bytes=raw_bytes,
    )
