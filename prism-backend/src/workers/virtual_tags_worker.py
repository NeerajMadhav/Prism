"""Celery tasks: virtual tag retroactive apply."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.services.virtual_tag_service import VirtualTagService
from src.workers import run_async_db
from src.workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="prism-virtual-tags.apply",
    max_retries=1,
    soft_time_limit=600,
    time_limit=630,
)
def apply_virtual_tags(self: Any, org_id: str, rule_id: str | None = None) -> dict[str, int]:
    rule_uuid = UUID(rule_id) if rule_id else None
    return run_async_db(
        lambda conn: VirtualTagService.apply_rules(conn, UUID(org_id), rule_uuid)
    )
