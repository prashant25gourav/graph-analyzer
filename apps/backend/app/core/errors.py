from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: str | None = None
    request_id: str | None = None
