import uuid
from dataclasses import dataclass
from enum import Enum

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

internal_ws_router = APIRouter()
ddv_client_ws_router = APIRouter()

logger = structlog.get_logger("rubintv")


class WorkerPodStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"


class Client:
    def __init__(self, client_id: str, websocket: WebSocket) -> None:
        """
        Represents a client connected to the WebSocket server.

        Parameters
        ----------
        client_id : `str`
            Unique identifier for the client.
        websocket : `WebSocket`
            WebSocket connection associated with the client.
        """
        self.client_id: str = client_id
        self.websocket: WebSocket = websocket


class WorkerPod(Client):
    def __init__(self, client_id: str, websocket: WebSocket) -> None:
        """
        Represents a worker pod that processes tasks from clients.

        Parameters
        ----------
        client_id : `str`
            Unique identifier for the worker pod.
        websocket : `WebSocket`
            WebSocket connection associated with the worker pod.
        """
        super().__init__(client_id, websocket)
        self.status: WorkerPodStatus = WorkerPodStatus.IDLE
        self.connected_client: Client | None = None

    async def process(self, message: str, client: Client) -> None:
        """Process a message from a client.

        Parameters
        ----------
        message : `str`
            The message to process.
        connected_client : `Client`
            The client that is connected to this worker pod.
        """
        self.status = WorkerPodStatus.BUSY
        self.connected_client = client
        await self.websocket.send_text(message)
        logger.info(
            "DDV: Worker started processing",
            worker_id=self.client_id,
            client_id=client.client_id,
        )

    async def on_finished(self, message: str) -> None:
        """Called when the worker pod has finished processing a message.

        Parameters
        ----------
        message : `str`
            The completion message to send to the client.
        """
        if self.connected_client is not None and message != "Client disconnected":
            try:
                logger.info("DDV: Worker sent", message=message)
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
    """Data class for queue items.

    Attributes
    ----------
    message : `str`
        The message to be processed.
    client : `Client`
        The client associated with the message.
    """

    message: str
    client: Client


class ConnectionManager:
    """Manages connections, worker tasks, and message queue."""

    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.workers: dict[str, WorkerPod] = {}
        self.queue: list[QueueItem] = []

    async def connect(self, websocket: WebSocket, connection_type: str) -> str:
        """
        Connects a new client or worker and returns their unique identifier.

        Parameters
        ----------
        websocket : `WebSocket`
            The WebSocket connection to register.
        connection_type : `str`
            Type of the client (``"client"`` or ``"worker"``). Only
            ``"worker"`` is positively matched against.

        Returns
        -------
        client_id : `str`
            The unique identifier for the connected entity.
        """
        client_id = str(uuid.uuid4())
        if connection_type == "worker":
            self.workers[client_id] = WorkerPod(client_id, websocket)
            logger.info("DDV: New worker connected", worker_id=client_id)
        else:
            self.clients[client_id] = Client(client_id, websocket)
            logger.info("DDV: New client connected", client_id=client_id)
        return client_id

    def disconnect(self, client_id: str) -> None:
        """
        Disconnects a client or worker.

        Parameters
        ----------
        client_id : `str`
            The unique identifier of the client or worker to disconnect.
        """
        if client_id in self.clients:
            logger.info("DDV: Client disconnected", client_id=client_id)
            del self.clients[client_id]
        if client_id in self.workers:
            logger.info("DDV: Worker disconnected", worker_id=client_id)
            del self.workers[client_id]

    async def broadcast(self, message: str, websocket: WebSocket) -> None:
        """
        Broadcasts a message to all connected clients and workers.

        Parameters
        ----------
        message : `str`
            The message to broadcast.
        websocket : `WebSocket`
            The WebSocket connection to use for broadcasting.
        """
        await websocket.send_text(message)
        logger.info("DDV: Broadcasting message", message=message)

    async def send_work_to_idle_worker(self, message: str, client: Client) -> None:
        """
        Sends work to an idle worker, or queues it if no idle workers are
        available.

        Parameters
        ----------
        message : `str`
            The message to be processed.
        client : `Client`
            The client that needs processing.
        """
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
        """
        Checks the queue and assigns a task to the specified worker if
        available.

        Parameters
        ----------
        worker : `WorkerPod`
            The worker that will process the next queued task if available.
        """
        if self.queue:
            queue_item = self.queue.pop(0)
            await worker.process(queue_item.message, queue_item.client)

    async def handle_client_message(self, client_id: str, message: str) -> None:
        """
        Handles incoming messages from clients by directing them to available
        workers.

        Parameters
        ----------
        client_id : `str`
            The identifier of the client sending the message.
        message : `str`
            The message to handle.
        """
        if client_id in self.clients:
            await self.send_work_to_idle_worker(message, self.clients[client_id])
            logger.info(
                "DDV: Handling client message", client_id=client_id, message=message
            )
        if client_id in self.workers:
            worker = self.workers[client_id]
            await worker.on_finished(message)
            await self.check_queue(worker)


@ddv_client_ws_router.websocket("/client")
async def ddv_client_ws_endpoint(websocket: WebSocket) -> None:
    """
    Endpoint for handling DDV client connections.

    Parameters
    ----------
    websocket : `WebSocket`
        The WebSocket connection for this endpoint.
    """
    await handle_connection(websocket, "client")


@internal_ws_router.websocket("/worker")
async def worker_ws_endpoint(websocket: WebSocket) -> None:
    """
    Endpoint for handling worker pod WebSocket connections.

    Parameters
    ----------
    websocket : `WebSocket`
        The WebSocket connection for this endpoint.
    """
    await handle_connection(websocket, "worker")


async def handle_connection(websocket: WebSocket, connection_type: str) -> None:
    try:
        await websocket.accept()
        logger.info("DDV: Websocket connection accepted")
        client_id = await manager.connect(websocket, connection_type)
        while True:
            data = await websocket.receive_text()
            logger.info("DDV: Received data", data=data)
            await manager.handle_client_message(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("DDV: WebSocket disconnected", client_id=client_id)


manager = ConnectionManager()
