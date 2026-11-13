"""Application error types."""


class AppError(Exception):
    """Intentional API error with HTTP status and optional machine code."""

    def __init__(self, message: str, status_code: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
