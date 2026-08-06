from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response


def metrics_endpoint() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
