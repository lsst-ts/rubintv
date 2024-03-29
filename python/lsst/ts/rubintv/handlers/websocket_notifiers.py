from typing import Any, Mapping
from uuid import UUID

import structlog
from fastapi import WebSocket
from lsst.ts.rubintv.handlers.websocket import remove_client_from_services
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from lsst.ts.rubintv.models.models import get_current_day_obs
from websockets import ConnectionClosed

logger = structlog.get_logger("rubintv")


async def notify_ws_clients(
    service: str, kind: str, loc_cam: str, payload: Any
) -> None:
    service_loc_cam_chan = " ".join([service, loc_cam])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    await notify_clients(to_notify, kind, payload)


async def notify_clients(
    clients_list: list[UUID], data_type: str, payload: Mapping
) -> None:
    async with clients_lock:
        for client_id in clients_list:
            websocket = clients[client_id]
            await _send_json(
                websocket,
                {
                    "dataType": data_type,
                    "payload": payload,
                    "datestamp": get_current_day_obs().isoformat(),
                },
            )


async def get_clients_to_notify(service_cam_id: str) -> list[UUID]:
    async with services_lock:
        to_notify = []
        if service_cam_id in services_clients:
            for client_id in services_clients[service_cam_id]:
                to_notify.append(client_id)
    return to_notify


async def notify_all_status_change(historical_busy: bool) -> None:
    key = "historicalStatus"
    async with services_lock:
        if key not in services_clients:
            return
        to_notify = services_clients[key]
    if to_notify:
        async with clients_lock:
            for client_id in to_notify:
                websocket = clients[client_id]
                await _send_json(
                    websocket,
                    {
                        "dataType": "historicalStatus",
                        "payload": historical_busy,
                    },
                )


async def _send_json(websocket: WebSocket, a_dict: dict) -> None:
    try:
        await websocket.send_json(a_dict)
    except ConnectionClosed:
        logger.info("Websocket disconnected uncleanly:", websocket=websocket)
        async with services_lock:
            if websocket in websocket_to_client:
                client_id = websocket_to_client[websocket]
                del clients[client_id]
                del websocket_to_client[websocket]
                await remove_client_from_services(client_id)
