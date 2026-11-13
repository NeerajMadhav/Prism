"""Retry helper with exponential backoff and 429 retry-after support."""

from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


class AuthError(Exception):
    """Non-retryable authentication failure (401)."""


class ForbiddenError(Exception):
    """Non-retryable authorization failure (403)."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (AuthError, ForbiddenError)):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return False
        return status >= 500 or status == 429
    return True


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
) -> T:
    """Run async fn with retries; honor Retry-After on 429."""
    last_error: Exception = RuntimeError("Unknown error")

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    ):
        with attempt:
            try:
                return await fn()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    retry_after = exc.response.headers.get("retry-after")
                    if retry_after and retry_after.isdigit():
                        wait_s = min(int(retry_after), 120)
                        # tenacity next wait will still apply; also sleep once here
                        import asyncio

                        await asyncio.sleep(wait_s)
                if exc.response.status_code == 401:
                    raise AuthError(str(exc)) from exc
                if exc.response.status_code == 403:
                    raise ForbiddenError(str(exc)) from exc
                raise
            except Exception as exc:
                last_error = exc
                raise

    raise last_error
