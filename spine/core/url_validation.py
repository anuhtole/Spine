"""Validate outbound URLs to reduce SSRF risk (webhooks, etc.)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = frozenset({"localhost", "metadata.google.internal"})


def _is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast


def validate_public_webhook_url(url: str, *, require_https: bool = True) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("Webhook URL must use http or https")
    host = (parsed.hostname or "").lower().strip(".")
    if parsed.scheme == "http" and require_https and host not in ("localhost", "127.0.0.1"):
        raise ValueError("Webhook URLs must use HTTPS")
    if not host or host in _BLOCKED_HOSTS:
        raise ValueError("Invalid webhook host")
    if host.endswith(".internal") or host.endswith(".local"):
        raise ValueError("Internal hostnames are not allowed")

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError("Webhook host could not be resolved") from exc

    for info in infos:
        ip_str = info[4][0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(addr):
            raise ValueError("Webhook URL must not target private or loopback addresses")

    return url
