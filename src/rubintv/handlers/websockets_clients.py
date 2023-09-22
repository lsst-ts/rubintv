from typing import Tuple

from fastapi import WebSocket

connected_clients: dict[WebSocket, Tuple[str, str]] = {}
status_clients: list[WebSocket] = []
