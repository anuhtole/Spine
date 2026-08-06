from fastapi import Depends, FastAPI, Header, HTTPException, status

from spine.api.deps import _admin_key_valid
from spine.api.metrics import metrics_endpoint
from spine.api.middleware.security import SecurityMiddleware
from spine.api.routes import (
    agents,
    api_keys,
    approvals,
    audit,
    auth,
    intercept,
    members,
    orgs,
    policies,
    sessions,
    verify,
    webhooks,
)
from spine.config.settings import settings
from spine.observability.otel import init_otel


def _require_metrics_access(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.metrics_require_admin_key:
        return
    if not _admin_key_valid(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def create_app() -> FastAPI:
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        title="Spine",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.add_middleware(SecurityMiddleware)
    init_otel(app)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_api_route(
        "/metrics",
        metrics_endpoint,
        methods=["GET"],
        include_in_schema=False,
        dependencies=[Depends(_require_metrics_access)],
    )

    app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(members.router, prefix="/v1/members", tags=["members"])
    app.include_router(api_keys.router, prefix="/v1/api-keys", tags=["api_keys"])
    app.include_router(intercept.router, prefix="/v1", tags=["intercept"])
    app.include_router(orgs.router, prefix="/v1/orgs", tags=["orgs"])
    app.include_router(agents.router, prefix="/v1/agents", tags=["agents"])
    app.include_router(policies.router, prefix="/v1/policies", tags=["policies"])
    app.include_router(verify.router, prefix="/v1/audit", tags=["audit_verify"])
    app.include_router(audit.router, prefix="/v1/audit", tags=["audit"])
    app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])
    app.include_router(approvals.router, prefix="/v1/approvals", tags=["approvals"])
    app.include_router(sessions.router, prefix="/v1/sessions", tags=["sessions"])

    return app


app = create_app()
