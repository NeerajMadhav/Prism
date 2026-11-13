"""Virtual tag rule engine for retroactive cost tagging."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from src.utils.logger import get_logger
from src.ws.ws_manager import worker_ws_broadcast

logger = get_logger(__name__)


def _field_value(record: dict[str, Any], field: str) -> Any:
    if field == "cost_usd":
        return float(record.get("cost_usd") or 0)
    if field.startswith("tag:"):
        key = field.split(":", 1)[1]
        tags = record.get("tags") or {}
        if isinstance(tags, str):
            tags = json.loads(tags)
        return tags.get(key)
    return record.get(field)


def _matches(record: dict[str, Any], condition: dict[str, Any]) -> bool:
    op = condition.get("op") or condition.get("operator")
    field = condition.get("field", "service")
    value = condition.get("value", "")
    current = _field_value(record, field)
    if op == "equals":
        return str(current) == str(value)
    if op == "contains":
        return value in str(current or "")
    if op == "starts_with":
        return str(current or "").startswith(str(value))
    if op == "regex":
        return bool(re.search(str(value), str(current or "")))
    if op == "greater_than":
        return float(current or 0) > float(value)
    if op == "less_than":
        return float(current or 0) < float(value)
    if op == "tag_exists":
        tags = record.get("tags") or {}
        if isinstance(tags, str):
            tags = json.loads(tags)
        return str(value) in tags
    if op == "tag_equals":
        tags = record.get("tags") or {}
        if isinstance(tags, str):
            tags = json.loads(tags)
        key = condition.get("key") or condition.get("tag_key") or value
        expected = condition.get("tag_value") or condition.get("expected")
        return tags.get(key) == expected
    return False


class VirtualTagService:
    """Apply virtual tag rules to historical cost records."""

    @staticmethod
    async def apply_rules(conn: Any, org_id: UUID, rule_id: UUID | None = None) -> dict[str, int]:
        audit_id = await conn.fetchval(
            """
            INSERT INTO virtual_tag_audit_log (org_id, rule_id, status)
            VALUES ($1, $2, 'running')
            RETURNING id
            """,
            org_id,
            rule_id,
        )
        rules = await conn.fetch(
            """
            SELECT * FROM virtual_tag_rules
            WHERE org_id = $1 AND is_active = TRUE
            ORDER BY priority ASC
            """,
            org_id,
        )
        processed = 0
        updated = 0
        offset = 0
        batch_size = 5000
        while True:
            rows = await conn.fetch(
                """
                SELECT id, service, region, cost_usd, tags
                FROM cost_records
                WHERE org_id = $1
                ORDER BY id
                LIMIT $2 OFFSET $3
                """,
                org_id,
                batch_size,
                offset,
            )
            if not rows:
                break
            for row in rows:
                processed += 1
                rec = dict(row)
                matched_rule = None
                for rule in rules:
                    conditions = rule["conditions"] or []
                    if isinstance(conditions, str):
                        conditions = json.loads(conditions)
                    if conditions and all(_matches(rec, c) for c in conditions):
                        matched_rule = rule
                        break
                if not matched_rule:
                    continue
                tags = rec.get("tags") or {}
                if isinstance(tags, str):
                    tags = json.loads(tags)
                tags = dict(tags)
                tags[matched_rule["tag_key"]] = matched_rule["tag_value"]
                await conn.execute(
                    "UPDATE cost_records SET tags = $2::jsonb WHERE id = $1",
                    row["id"],
                    json.dumps(tags),
                )
                updated += 1
            worker_ws_broadcast(
                str(org_id),
                "virtual_tags.progress",
                {"processed": processed, "updated": updated},
            )
            offset += batch_size

        await conn.execute(
            """
            UPDATE virtual_tag_audit_log
            SET status = 'completed', finished_at = NOW(),
                rows_processed = $2, rows_updated = $3
            WHERE id = $1
            """,
            audit_id,
            processed,
            updated,
        )
        return {"processed": processed, "updated": updated}
