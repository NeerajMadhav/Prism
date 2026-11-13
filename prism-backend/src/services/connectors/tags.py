"""Tag normalization shared by cloud connectors."""



def normalize_tags(raw: dict[str, str] | list[dict[str, str]] | None) -> dict[str, str]:
    """Lowercase tag keys and strip values (unified schema)."""
    if not raw:
        return {}
    out: dict[str, str] = {}
    if isinstance(raw, list):
        for item in raw:
            key = str(item.get("Key") or item.get("key") or "").lower().strip()
            val = str(item.get("Value") or item.get("value") or "").strip()
            if key:
                out[key] = val
    else:
        for key, value in raw.items():
            out[str(key).lower().strip()] = str(value).strip()
    return out
