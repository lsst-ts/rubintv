import uuid

from fastapi import APIRouter, WebSocket
from lsst.ts.rubintv.handlers.websockets_clients import (
    heartbeat_clients,
    heartbeat_lock,
)

heartbeat_router = APIRouter()


@heartbeat_router.websocket("/")
async def heartbeatServer(websocket: WebSocket) -> None:
    await websocket.accept()

    client_id = uuid.uuid4()
    await websocket.send_text(str(client_id))

    async with heartbeat_lock:
        heartbeat_clients[client_id] = websocket
