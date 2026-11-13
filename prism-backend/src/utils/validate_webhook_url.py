"""SSRF protection for customer-supplied webhook URLs."""

import ipaddress
import socket
from urllib.parse import urlparse

from src.utils.errors import AppError


def _is_blocked_ip(ip: str) -> bool:
    """Block loopback, RFC1918, link-local, multicast, reserved, unspecified."""
    addr = ipaddress.ip_address(ip)
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def validate_webhook_url(url: str) -> None:
    """Validate URL at save time; raise AppError if unsafe."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise AppError("Webhook URL must use https://", status_code=400)
    if not parsed.hostname:
        raise AppError("Webhook URL hostname is invalid", status_code=400)
    if parsed.username or parsed.password:
        raise AppError("Webhook URL must not include credentials", status_code=400)
    try:
        infos = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AppError("Webhook URL hostname cannot be resolved", status_code=400) from exc
    if not infos:
        raise AppError("Webhook URL hostname cannot be resolved", status_code=400)
    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise AppError("Webhook URL must not resolve to a private IP", status_code=400)


def verify_dispatch_url(url: str) -> bool:
    """Re-check DNS at dispatch time (DNS rebinding protection)."""
    try:
        validate_webhook_url(url)
        return True
    except AppError:
        return False
