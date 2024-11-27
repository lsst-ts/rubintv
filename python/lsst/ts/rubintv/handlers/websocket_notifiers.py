import asyncio
import base64
import gzip
import json
from typing import Any, Mapping
from uuid import UUID

from fastapi import WebSocket
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs

logger = rubintv_logger()


async def notify_ws_clients(
    service: Service, message_type: MessageType, loc_cam: str, payload: Any
) -> None:
    service_loc_cam_chan = " ".join([service.value, loc_cam])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    await notify_clients(to_notify, service, message_type, payload)


async def notify_clients(
    clients_list: list[UUID],
    service: Service,
    message_type: MessageType,
    payload: Mapping,
) -> None:
    tasks = []
    async with clients_lock:
        for client_id in clients_list:
            if client_id in clients:
                websocket = clients[client_id]
                task = asyncio.create_task(
                    send_notification(websocket, service, message_type, payload)
                )
                tasks.append(task)
    # `return_exceptions=True` prevents one failed task from affecting others
    await asyncio.gather(*tasks, return_exceptions=True)


async def send_notification(
    websocket: WebSocket, service: Service, messageType: MessageType, payload: Any
) -> None:
    datestamp = get_current_day_obs().isoformat()
    if messageType is MessageType.CAMERA_PD_BACKDATED and payload:
        # use the day_obs in the backdated event, rather than today
        datestamp = payload.values()[0].get("day_obs", datestamp)
    try:
        payload_string = json.dumps(payload)
        zipped = gzip.compress(bytes(payload_string, "utf-8"))
        encoded = base64.b64encode(zipped).decode("utf-8")
        await websocket.send_json(
            {
                "service": service.value,
                "dataType": messageType.value,
                "payload": encoded,
                "datestamp": datestamp,
            }
        )
    except Exception as e:
        logger.error(f"Failed to send notification to {websocket}: {str(e)}")


async def get_clients_to_notify(service_cam_id: str) -> list[UUID]:
    async with services_lock:
        to_notify = []
        if service_cam_id in services_clients:
            for client_id in services_clients[service_cam_id]:
                to_notify.append(client_id)
    return to_notify


async def notify_all_status_change(historical_busy: bool) -> None:
    service = Service.HISTORICALSTATUS
    messageType = MessageType.HISTORICAL_STATUS
    key = service.value
    tasks = []
    async with services_lock:
        if key not in services_clients:
            return
        client_ids = services_clients[key]

    # Gather websockets for the clients
    async with clients_lock:
        websockets = [
            clients[client_id] for client_id in client_ids if client_id in clients
        ]

    # Prepare tasks for each websocket
    for websocket in websockets:
        task = send_notification(websocket, service, messageType, historical_busy)
        tasks.append(task)

    # Use asyncio.gather to handle all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
