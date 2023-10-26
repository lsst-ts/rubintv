import json
import re
import uuid

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from rubintv.models.models import Camera, Location
from rubintv.models.models_helpers import find_first

ws_router = APIRouter()

valid_services = ["camera", "channel", "nightreport"]


@ws_router.websocket("/")
async def data_websocket(
    websocket: WebSocket,
) -> None:
    logger = structlog.get_logger(__name__)
    await websocket.accept()

    client_id = uuid.uuid4()
    await websocket.send_text(str(client_id))

    async with clients_lock:
        clients[client_id] = websocket
        websocket_to_client[websocket] = client_id

    try:
        while True:
            raw: str = await websocket.receive_text()
            try:
                data: dict = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error("JSON not well formed", error=e)
                continue
            if not await is_valid_client_request(data):
                logger.error("Not valid request", data=data)
                continue
            r_client_id = uuid.UUID(data["clientID"])
            if "messageType" not in data:
                logger.warn(
                    "No message type found in data from client",
                    client_id=r_client_id,
                    data=data,
                )
                continue
            message_type = data["messageType"]
            match message_type:
                case "service":
                    if "message" in data:
                        service = data["message"]
                        logger.info(
                            "Attaching:",
                            client_id=r_client_id,
                            service=service,
                        )
                        await attach_service(r_client_id, service, websocket)
                    else:
                        logger.warn(
                            "No service found in message from client",
                            client_id=r_client_id,
                        )
                    continue
                case "historicalStatus":
                    historical_busy = (
                        await websocket.app.state.historical.is_busy()
                    )
                    await websocket.send_json(
                        {
                            "dataType": "historicalStatus",
                            "payload": historical_busy,
                        }
                    )
                    async with services_lock:
                        if "historicalStatus" not in services_clients:
                            services_clients["historicalStatus"] = [
                                r_client_id
                            ]
                        else:
                            services_clients["historicalStatus"].append(
                                r_client_id
                            )
    except WebSocketDisconnect:
        async with clients_lock:
            if websocket in websocket_to_client:
                client_id = websocket_to_client[websocket]
                del clients[client_id]
                del websocket_to_client[websocket]
                await remove_client_from_services(client_id)


async def remove_client_from_services(client_id: uuid.UUID) -> None:
    async with services_lock:
        # First remove the client_id from all services
        for _, client_ids in services_clients.items():
            if client_id in client_ids:
                client_ids.remove(client_id)

        # Then collect the services that have no more associated client IDs
        services_to_remove = [
            service
            for service, client_ids in services_clients.items()
            if not client_ids
        ]

        # Finally, delete those services
        for service in services_to_remove:
            del services_clients[service]


async def attach_service(
    client_id: uuid.UUID, service_loc_cam: str, websocket: WebSocket
) -> None:
    logger = structlog.get_logger(__name__)
    if not await is_valid_service(service_loc_cam):
        logger.error(
            "Bad request", service_loc=service_loc_cam, client_id=client_id
        )
        return
    try:
        service, loc_cam = service_loc_cam.split(" ")
    except ValueError:
        logger.error("Bad request", service=service, client_id=client_id)
        return

    location, camera_name, *extra = loc_cam.split("/")
    locations = websocket.app.state.models.locations
    if not (
        camera := await is_valid_location_camera(
            location, camera_name, locations
        )
    ):
        logger.error("No such camera", service=service, client_id=client_id)
        return
    if extra:
        channel = extra[0]
        if not await is_valid_channel(camera, channel):
            logger.error(
                "No such channel", service=service, client_id=client_id
            )
            return

    # await websocket.send_text(f"OK/{service_loc_cam}")

    async with services_lock:
        if service in services_clients:
            services_clients[service_loc_cam].append(client_id)
        else:
            services_clients[service_loc_cam] = [client_id]


async def is_valid_client_request(data: dict) -> bool:
    logger = structlog.get_logger(__name__)
    try:
        client_id = uuid.UUID(data["clientID"])
    except (KeyError, ValueError):
        logger.warn("Received json without client_id")
        return False
    return client_id in clients.keys()


async def is_valid_service(service: str) -> bool:
    services_str = "|".join(valid_services)
    valid_req = re.compile(rf"^({services_str}) \w+(\/\w+)+$")
    return valid_req.fullmatch(service) is not None


async def is_valid_location_camera(
    location_name: str, camera_name: str, locations: list[Location]
) -> Camera | None:
    location: Location | None
    if not (location := find_first(locations, "name", location_name)):
        return None
    camera: Camera | None
    if not (camera := find_first(location.cameras, "name", camera_name)):
        return None
    if not camera.online:
        return None
    return camera


async def is_valid_channel(camera: Camera, channel_name: str) -> bool:
    return camera.channels is not None and channel_name in [
        chan.name for chan in camera.channels
    ]
