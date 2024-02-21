from typing import Any, Mapping
from uuid import UUID

from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
)
from lsst.ts.rubintv.models.models import get_current_day_obs


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
            await websocket.send_json(
                {
                    "dataType": data_type,
                    "payload": payload,
                    "datestamp": get_current_day_obs().isoformat(),
                }
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
                await websocket.send_json(
                    {
                        "dataType": "historicalStatus",
                        "payload": historical_busy,
                    }
                )
