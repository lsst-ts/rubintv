"""Internal HTTP handlers that serve relative to the root path, ``/``.

These handlers aren't externally visible since the app is available at a path,
``/rubintv``. See `rubintv.handlers.external` for
the external endpoint handlers.

These handlers should be used for monitoring, health checks, internal status,
or other information that should not be visible outside the Kubernetes cluster.
"""

from datetime import datetime
from json import JSONDecodeError

import structlog
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect

from ..models.models import Heartbeat, Metadata

__all__ = ["get_index", "internal_router"]

logger = structlog.get_logger("rubintv")
internal_router = APIRouter()
"""FastAPI router for all internal handlers."""

heartbeats: dict[str, Heartbeat] = {}


@internal_router.get(
    "/",
    description=(
        "Return metadata about the running application. Can also be used as"
        " a health check. This route is not exposed outside the cluster and"
        " therefore cannot be used by external clients."
    ),
    include_in_schema=False,
    response_model=Metadata,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index() -> Metadata:
    """GET ``/`` (the app's internal root).

    By convention, this endpoint returns only the application's metadata.
    """
    return Metadata()


"""
Structure of internal message json:
{
    serviceName:    str (f"{camera_name}-{channel_name}")
    timeSent:       int,
    timeNext:       int
}
"""


@internal_router.websocket("/heartbeat_listener")
async def heartbeat_listener(
    websocket: WebSocket, background_tasks: BackgroundTasks
) -> None:
    await websocket.accept()
    try:
        msg = await websocket.receive_json(mode="text")
        background_tasks.add_task(process_heartbeat_msg, msg)
    except (JSONDecodeError, ValueError, WebSocketDisconnect) as e:
        if type(e) is JSONDecodeError or type(e) is ValueError:
            logger.error("Received non-JSON heartbeat message:", message=msg)
        else:
            logger.error("Heartbeat websocket disconnected")


async def process_heartbeat_msg(msg: dict) -> None:
    service_name = msg["service_name"]
    next_expected = datetime.fromtimestamp(msg["next_expected"])
    if service_name in heartbeats:
        heartbeats[service_name].update_heartbeat(next_expected)
    else:
        heartbeats[service_name] = Heartbeat(service_name, next_expected)
