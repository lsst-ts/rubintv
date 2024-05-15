import asyncio
from typing import Any, Mapping
from uuid import UUID

import structlog
from fastapi import WebSocket
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.handlers.handlers_helpers import (
    get_camera_current_data,
    get_current_night_report_payload,
)
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
)
from lsst.ts.rubintv.models.models import Camera, Location
from lsst.ts.rubintv.models.models import ServiceMessageTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs

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
    tasks = []
    async with clients_lock:
        logger.info("Sending updates to:", num_clients=len(clients_list))
        for client_id in clients_list:
            if client_id in clients:
                websocket = clients[client_id]
                task = asyncio.create_task(
                    send_notification(websocket, data_type, payload)
                )
                tasks.append(task)
    # `return_exceptions=True` prevents one failed task from affecting others
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Finished sending updates")


async def notify_ws_of_latest(
    websocket: WebSocket,
    service_loc_cam: str,
    location: Location,
    camera: Camera,
    channel_name: str,
    service: str,
) -> None:
    match service:
        case "camera":
            data = await get_camera_current_data(
                location, camera, websocket, use_historical=False
            )
            if data is None:
                return
            day_obs, channel_data, per_day, metadata, nr_exists, is_historical = data
            await send_notification(websocket, Service.CAMERA_TABLE, channel_data)
            await send_notification(websocket, Service.CAMERA_METADATA, metadata)
            await send_notification(websocket, Service.CAMERA_PER_DAY, per_day)
            if nr_exists:
                await send_notification(
                    websocket, Service.CAMERA_PER_DAY, "nightReportExists"
                )
        case "channel":
            current_poller: CurrentPoller = websocket.app.state.current_poller
            event = await current_poller.get_current_channel_event(
                location.name, camera.name, channel_name
            )
            await send_notification(websocket, Service.CHANNEL_EVENT, event.__dict__)
        case "nightreport":
            day_obs, night_report = await get_current_night_report_payload(
                location, camera, websocket
            )
            await send_notification(websocket, Service.NIGHT_REPORT, night_report)


async def send_notification(
    websocket: WebSocket, data_type: Service, payload: Any
) -> None:
    try:
        await websocket.send_json(
            {
                "dataType": data_type.value,
                "payload": payload,
                "datestamp": get_current_day_obs().isoformat(),
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
    key = "historicalStatus"
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
        task = send_notification(websocket, "historicalStatus", historical_busy)
        tasks.append(task)

    # Use asyncio.gather to handle all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
