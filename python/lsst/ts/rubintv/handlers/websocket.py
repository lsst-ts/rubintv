import json
import re
import traceback
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import send_notification
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from lsst.ts.rubintv.models.models import Camera, Location
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models_helpers import find_first

data_ws_router = APIRouter()
logger = rubintv_logger()

valid_services = [Service.value for Service in Service]


@data_ws_router.websocket("/")
async def data_websocket(
    websocket: WebSocket,
) -> None:
    try:
        await websocket.accept()
        client_id = uuid.uuid4()
        await websocket.send_text(str(client_id))

        async with clients_lock:
            clients[client_id] = websocket
            websocket_to_client[websocket] = client_id
            logger.info("Num clients:", num_clients=len(clients))

        while True:
            raw: str = await websocket.receive_text()
            logger.info("Ws recvd:", raw=raw)
            validated = await validate_raw_message(raw)
            if validated is None:
                continue
            r_client_id, data = validated

            if "message" in data:
                service_loc_cam = data["message"]
                logger.info("Attaching:", id=r_client_id, service=service_loc_cam)
                await attach_service(r_client_id, service_loc_cam, websocket)
            else:
                logger.warn("No message:", client_id=r_client_id, data=data)

    except WebSocketDisconnect:
        async with clients_lock:
            if websocket in websocket_to_client:
                client_id = websocket_to_client[websocket]
                logger.info("Unattaching:", client_id=client_id)
                del clients[client_id]
                del websocket_to_client[websocket]
                logger.info("Num clients:", num_clients=len(clients))
                await remove_client_from_services(client_id)
    except Exception as e:
        # Catch all exceptions to prevent the websocket from crashing
        logger.error(
            "Unexpected error in websocket handler",
            error=e,
            traceback=traceback.format_exc(),
        )


async def validate_raw_message(raw: str) -> tuple[uuid.UUID, dict] | None:
    try:
        data: dict = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON not well formed", error=e)
        return None
    if not await is_valid_client_request(data):
        logger.error("Not valid request", data=data)
        return None
    r_client_id = uuid.UUID(data["clientID"])
    return r_client_id, data


async def remove_client_from_services(client_id: uuid.UUID) -> None:
    logger.info("Removing client from services list...", client_id=client_id)
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
    logger.info("Removed client.")


async def attach_simple_service(
    client_id: uuid.UUID,
    websocket: WebSocket,
    service: Service,
    message_type: MessageType,
    service_key: str,
) -> None:
    """Attach a client to a simple service that just needs initial state
    notification.

    Parameters
    ----------
    client_id : uuid.UUID
        The ID of the client to attach
    websocket : WebSocket
        The websocket connection
    service : Service
        The service type (e.g. HISTORICALSTATUS, DETECTORS)
    message_type : MessageType
        The type of message to send
    service_key : str
        The key to use for storing in services_clients
    """
    # Register client for this service
    async with services_lock:
        if service_key not in services_clients:
            services_clients[service_key] = [client_id]
        else:
            services_clients[service_key].append(client_id)

    payload = None
    if service == Service.HISTORICALSTATUS:
        payload = await websocket.app.state.historical.is_busy()
    elif service == Service.DETECTORS:
        if hasattr(websocket.app.state, "redis_subscriber"):
            payload = await websocket.app.state.redis_subscriber.read_initial_state()
    if payload:
        await send_notification(
            websocket,
            service,
            message_type,
            payload,
        )


async def attach_service(
    client_id: uuid.UUID, full_service_name: str, websocket: WebSocket
) -> None:
    """Attach a client to a service based on the full service name.
    The full service name is expected to be in the format:
    "ServiceName Location/Camera[/Channel]".
    If the service is historicalStatus or detectors, it will attach
    to a simple service that just needs initial state notification.

    Parameters
    ----------
    client_id : uuid.UUID
        The ID of the client to attach
    full_service_name : str
        The full service name in the format
        "ServiceName Location/Camera[/Channel]"
    websocket : WebSocket
        The websocket connection
    """
    if full_service_name == "historicalStatus":
        await attach_simple_service(
            client_id,
            websocket,
            Service.HISTORICALSTATUS,
            MessageType.HISTORICAL_STATUS,
            "historicalStatus",
        )
        return
    elif full_service_name == "detectors":
        await attach_simple_service(
            client_id,
            websocket,
            Service.DETECTORS,
            MessageType.DETECTOR_STATUS,
            "detectors",
        )
        return

    try:
        service_str, full_location = full_service_name.split(" ")
        service = Service[service_str.upper()]
    except ValueError:
        logger.error("Bad request", service=service_str, client_id=client_id)
        return

    channel_name = ""
    location_name, camera_name, *extra = full_location.split("/")
    locations = websocket.app.state.models.locations
    if not (
        camera := await is_valid_location_camera(location_name, camera_name, locations)
    ):
        logger.error(
            "No such camera:",
            service=service,
            client_id=client_id,
            camera=full_location,
        )
        return

    location = find_first(locations, "name", location_name)

    if extra:
        channel_name = extra[0]
        if not await is_valid_channel(camera, channel_name):
            logger.error("No such channel", service=service, client_id=client_id)
            return

    await notify_new_client(websocket, location, camera, channel_name, service)

    async with services_lock:
        if full_service_name in services_clients:
            services_clients[full_service_name].append(client_id)
        else:
            services_clients[full_service_name] = [client_id]

    # If registering a service with location and camera and channel,
    # also register a service with just location and camera.
    if not channel_name:
        return

    loc_cam_service = f"{service_str} {location_name}/{camera_name}"

    async with services_lock:
        if loc_cam_service in services_clients:
            services_clients[loc_cam_service].append(client_id)
        else:
            services_clients[loc_cam_service] = [client_id]


async def is_valid_client_request(data: dict) -> bool:
    try:
        client_id = uuid.UUID(data["clientID"])
    except (KeyError, ValueError, TypeError):
        logger.warn("Received json without client_id")
        return False
    return client_id in clients.keys()


async def is_valid_service(service: str) -> bool:
    services_str = "|".join(valid_services)
    valid_req = re.compile(rf"^({services_str}) [\w-]+(\/\w+)+$")
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


async def notify_new_client(
    websocket: WebSocket,
    location: Location,
    camera: Camera,
    channel_name: str,
    service: Service,
) -> None:
    current_poller: CurrentPoller = websocket.app.state.current_poller
    async for message_type, data in current_poller.get_latest_data(
        location, camera, channel_name, service
    ):
        await send_notification(websocket, service, message_type, data)
