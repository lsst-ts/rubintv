import uuid
from dataclasses import dataclass
from enum import Enum

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ddv_ws_router = APIRouter()
logger = structlog.get_logger(__name__)


class WorkerPodStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"


class Client:
    def __init__(self, client_id: str, websocket: WebSocket) -> None:
        self.client_id: str = client_id
        self.websocket: WebSocket = websocket


class WorkerPod(Client):
    def __init__(self, client_id: str, websocket: WebSocket) -> None:
        super().__init__(client_id, websocket)
        self.status: WorkerPodStatus = WorkerPodStatus.IDLE
        self.connected_client: Client | None = None

    async def process(self, message: str, client: Client) -> None:
        self.status = WorkerPodStatus.BUSY
        self.connected_client = client
        await self.websocket.send_text(message)
        logger.info(
            "DDV: Worker started processing",
            worker_id=self.client_id,
            client_id=client.client_id,
        )

    async def on_finished(self, message: str) -> None:
        if self.connected_client is not None and message != "Client disconnected":
            try:
                await self.connected_client.websocket.send_text(message)
            except WebSocketDisconnect:
                logger.info(
                    "DDV: Worker finished but client disconnected",
                    worker_id=self.client_id,
                    message=message,
                )
        else:
            logger.info(
                "DDV: Worker finished but no client connected",
                worker_id=self.client_id,
                message=message,
            )
        self.status = WorkerPodStatus.IDLE
        self.connected_client = None


@dataclass
class QueueItem:
    message: str
    client: Client


class ConnectionManager:
    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.workers: dict[str, WorkerPod] = {}
        self.queue: list[QueueItem] = []

    async def connect(self, websocket: WebSocket, client_type: str) -> str:
        client_id = str(uuid.uuid4())
        if client_type == "worker":
            self.workers[client_id] = WorkerPod(client_id, websocket)
            logger.info("DDV: New worker connected", worker_id=client_id)
        else:
            self.clients[client_id] = Client(client_id, websocket)
            logger.info("DDV: New client connected", client_id=client_id)
        return client_id

    def disconnect(self, client_id: str) -> None:
        if client_id in self.clients:
            logger.info("DDV: Client disconnected", client_id=client_id)
            del self.clients[client_id]
        if client_id in self.workers:
            logger.info("DDV: Worker disconnected", worker_id=client_id)
            del self.workers[client_id]

    async def broadcast(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)
        logger.info("DDV: Broadcasting message", message=message)

    async def send_work_to_idle_worker(self, message: str, client: Client) -> None:
        idle_worker = next(
            (
                worker
                for worker in self.workers.values()
                if worker.status == WorkerPodStatus.IDLE
            ),
            None,
        )
        if idle_worker:
            await idle_worker.process(message, client)
        else:
            self.queue.append(QueueItem(message, client))
            logger.info("DDV: Message queued", message=message)

    async def check_queue(self, worker: WorkerPod) -> None:
        if self.queue:
            queue_item = self.queue.pop(0)
            await worker.process(queue_item.message, queue_item.client)

    async def handle_client_message(self, client_id: str, message: str) -> None:
        if client_id in self.clients:
            await self.send_work_to_idle_worker(message, self.clients[client_id])
            logger.info(
                "DDV: Handling client message", client_id=client_id, message=message
            )
        if client_id in self.workers:
            worker = self.workers[client_id]
            await worker.on_finished(message)
            await self.check_queue(worker)


@ddv_ws_router.websocket("/ws/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str) -> None:
    client_id = await manager.connect(websocket, client_type)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_client_message(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("DDV: WebSocket disconnected", client_id=client_id)


manager = ConnectionManager()
