import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets import ConnectionClosed

heartbeat_sockets: list[WebSocket] = []
heartbeats_sock_lock = asyncio.Lock()
broadcast_task = None  # Reference to the broadcast task

heartbeat_router = APIRouter()

logger = structlog.get_logger("rubintv")


async def send_heartbeat(socket: WebSocket) -> None:
    try:
        await socket.send_text("heartbeat!")
    except (WebSocketDisconnect, ConnectionClosed):
        logger.info("Heartbeat websocket disconnected", websocket=socket)
        async with heartbeats_sock_lock:
            if socket in heartbeat_sockets:
                heartbeat_sockets.remove(socket)
                logger.info("Removed disconnected websocket", websocket=socket)


async def broadcast_heartbeats() -> None:
    while True:
        async with heartbeats_sock_lock:
            tasks = [send_heartbeat(socket) for socket in heartbeat_sockets]
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)


@heartbeat_router.websocket("/")
async def heartbeat_server(websocket: WebSocket) -> None:
    global broadcast_task
    await websocket.accept()
    # initial_state = [hb.to_json() for hb in heartbeats.values()]
    # await websocket.send_json(initial_state)
    logger.info("Adding heartbeats broadcaster")
    async with heartbeats_sock_lock:
        heartbeat_sockets.append(websocket)
        if broadcast_task is None or broadcast_task.done():
            broadcast_task = asyncio.create_task(broadcast_heartbeats())
            logger.info("Started broadcast heartbeats task")

    try:
        while True:
            # Keep the connection alive or perform other operations as needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", websocket=websocket)
        async with heartbeats_sock_lock:
            if websocket in heartbeat_sockets:
                heartbeat_sockets.remove(websocket)
                logger.info("Removed websocket", websocket=websocket)
