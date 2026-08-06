from __future__ import annotations

from typing import Any

import jwt
from jwt import PyJWKClient

from spine.config.settings import settings


def decode_bearer_token(token: str) -> dict[str, Any] | None:
    if not settings.oidc_jwks_url or not settings.oidc_audience:
        return None

    jwks = PyJWKClient(settings.oidc_jwks_url)
    signing_key = jwks.get_signing_key_from_jwt(token)
    options = {
        "verify_signature": True,
        "verify_aud": True,
    }
    algs = [a.strip() for a in settings.oidc_jwt_algorithms.split() if a.strip()]
    decode_kwargs: dict[str, Any] = {
        "algorithms": algs,
        "audience": settings.oidc_audience,
        "options": options,
    }
    if settings.oidc_issuer:
        decode_kwargs["issuer"] = settings.oidc_issuer
    return jwt.decode(token, signing_key.key, **decode_kwargs)  # type: ignore[arg-type]


def has_role(claims: dict[str, Any], role: str) -> bool:
    # Common patterns: "roles": ["a","b"] OR "role": "x"
    roles = claims.get("roles")
    if isinstance(roles, list) and role in [str(x) for x in roles]:
        return True
    if isinstance(roles, str) and roles == role:
        return True
    if str(claims.get("role", "")) == role:
        return True
    # Namespaced role claims (legacy + current)
    for claim_key in ("https://spine.dev/roles", "https://guts.dev/roles"):
        namespaced = claims.get(claim_key)
        if isinstance(namespaced, list) and role in [str(x) for x in namespaced]:
            return True
    return False
