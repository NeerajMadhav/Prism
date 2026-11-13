"""Pagination helpers for list endpoints."""

from math import ceil
from typing import Any

from fastapi import Request


def get_pagination(request: Request, default_limit: int = 20, max_limit: int = 100) -> dict[str, int]:
    """Parse page/limit from query params."""
    try:
        page = max(1, int(request.query_params.get("page", "1")))
    except ValueError:
        page = 1
    try:
        limit = int(request.query_params.get("limit", str(default_limit)))
    except ValueError:
        limit = default_limit
    limit = max(1, min(limit, max_limit))
    offset = (page - 1) * limit
    return {"page": page, "limit": limit, "offset": offset}


def paginated_response(data: list[Any], total: int, page: int, limit: int) -> dict[str, Any]:
    """Wrap list data with pagination metadata."""
    pages = ceil(total / limit) if limit else 0
    return {
        "data": data,
        "pagination": {"total": total, "page": page, "limit": limit, "pages": pages},
    }
