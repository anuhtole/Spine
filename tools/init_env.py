"""Generate a local .env with real secrets.

Copies .env.example and replaces the placeholder secrets with freshly
generated random values. The dashboard BFF refuses to start on the
placeholder values (deliberately — they are known strings), so a fresh
clone needs real ones before anything will come up.

Run directly, or let `make demo` call it. Never overwrites an existing .env.
"""

from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"

# Keys that must be unique per install. Anything still holding one of the
# placeholder values below gets a generated replacement.
GENERATED_KEYS = ("ADMIN_API_KEY", "SESSION_SECRET", "JWT_SECRET")

PLACEHOLDERS = {
    "",
    "change-me",
    "change-me-long-random-string",
    "dev-change-me-in-production",
}


def main() -> int:
    if TARGET.exists():
        print(".env already exists — leaving it alone.")
        return 0

    if not EXAMPLE.exists():
        print("ERROR: .env.example not found.")
        return 1

    lines = EXAMPLE.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    seen: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, value = stripped.split("=", 1)
            key = key.strip()
            if key in GENERATED_KEYS and value.strip() in PLACEHOLDERS:
                out.append(f"{key}={secrets.token_urlsafe(32)}")
                seen.add(key)
                continue
        out.append(line)

    # JWT_SECRET is commented out in the example; add it explicitly rather
    # than letting it fall back to ADMIN_API_KEY.
    missing = [k for k in GENERATED_KEYS if k not in seen]
    if missing:
        out.append("")
        out.append("# Generated locally by tools/init_env.py")
        out.extend(f"{key}={secrets.token_urlsafe(32)}" for key in missing)

    TARGET.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Created .env with generated secrets for: {', '.join(GENERATED_KEYS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
