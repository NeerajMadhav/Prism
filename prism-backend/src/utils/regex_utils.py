"""ReDoS-safe regex validation for virtual tag rules."""

import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from src.utils.errors import AppError

_executor = ThreadPoolExecutor(max_workers=2)


def validate_regex_pattern(pattern: str) -> None:
    """Reject invalid or catastrophic regex patterns."""
    if len(pattern) > 200:
        raise AppError("Regex pattern must be at most 200 characters", status_code=400)
    try:
        re.compile(pattern)
    except re.error as exc:
        raise AppError(f"Invalid regex pattern: {exc}", status_code=400) from exc
    if not safe_regex_test(pattern):
        raise AppError("Regex pattern has catastrophic backtracking risk", status_code=400)


def safe_regex_test(pattern: str, timeout_ms: int = 50) -> bool:
    """Return True if pattern completes on a 1000-char string within timeout."""

    def _run() -> bool:
        re.search(pattern, "a" * 1000)
        return True

    future = _executor.submit(_run)
    try:
        return future.result(timeout=timeout_ms / 1000)
    except FuturesTimeoutError:
        return False
    except re.error:
        return False
