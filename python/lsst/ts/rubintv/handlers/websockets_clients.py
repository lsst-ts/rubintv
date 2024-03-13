import asyncio
import uuid

from fastapi import WebSocket

# keyed by websocket
clients: dict[uuid.UUID, WebSocket] = {}
websocket_to_client: dict[WebSocket, uuid.UUID] = {}
# keyed by service_id
services_clients: dict[str, list[uuid.UUID]] = {}
clients_lock = asyncio.Lock()
services_lock = asyncio.Lock()

heartbeat_clients: dict[uuid.UUID, WebSocket] = {}
heartbeat_lock = asyncio.Lock()
