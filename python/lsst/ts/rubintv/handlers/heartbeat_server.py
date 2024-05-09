import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets import ConnectionClosed

HEARTBEAT_INTERVAL = 5

heartbeat_sockets: list[WebSocket] = []
heartbeats_sock_lock = asyncio.Lock()

broadcast_task = None  # Reference to the broadcast task

heartbeat_router = APIRouter()
logger = structlog.get_logger("rubintv")


async def remove_websocket(websocket: WebSocket) -> None:
    """Applies lock to safely remove websocket ref. from list of connected
    clients.

    Parameters
    ----------
    websocket : WebSocket
        The given websocket.
    """
    async with heartbeats_sock_lock:
        if websocket in heartbeat_sockets:
            heartbeat_sockets.remove(websocket)
            logger.info("Removed websocket", websocket=websocket)


async def send_heartbeat(websocket: WebSocket) -> None:
    """Send simple test string to single websocket.

    Parameters
    ----------
    websocket : WebSocket
        The given websocket.
    """
    try:
        await websocket.send_text("heartbeat!")
    except (WebSocketDisconnect, ConnectionClosed):
        logger.info("Heartbeat websocket disconnected", websocket=websocket)
        await remove_websocket(websocket)


async def broadcast_heartbeats() -> None:
    """Create task for each connected websocket to broadcast heartbeats.

    If one websocket blocks, the broadcast to others won't be blocked.
    """
    while True:
        async with heartbeats_sock_lock:
            tasks = [send_heartbeat(socket) for socket in heartbeat_sockets]
        await asyncio.gather(*tasks)
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@heartbeat_router.websocket("/")
async def heartbeat_server(websocket: WebSocket) -> None:
    """Route that adds a websocket connection, solely for broadcasting
    heartbeat data. Only one connection is made per browser and is
    handled client-side by a shared worker.

    Parameters
    ----------
    websocket : WebSocket
        The new websocket object.
    """
    global broadcast_task
    await websocket.accept()
    logger.info("Adding heartbeats broadcaster")
    async with heartbeats_sock_lock:
        heartbeat_sockets.append(websocket)
        if broadcast_task is None or broadcast_task.done():
            broadcast_task = asyncio.create_task(broadcast_heartbeats())
            logger.info("Started broadcast heartbeats task")

    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", websocket=websocket)
        await remove_websocket(websocket)
