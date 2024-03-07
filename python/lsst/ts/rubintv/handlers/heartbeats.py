from fastapi import APIRouter, WebSocket

heartbeat_router = APIRouter()


@heartbeat_router.websocket("/")
async def heartbeatServer(websocket: WebSocket) -> None:
    await websocket.accept()
