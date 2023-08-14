import re
from typing import Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Event, Location

ws_router = APIRouter()
connected_clients: dict[WebSocket, Tuple[str, str]] = {}


@ws_router.websocket("/")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Websocket endpoint for proving updates for camera data, channels or
    night reports.

    Clients wanting to connect to an updater should send either:

        `"camera <location_name>/<camera_name>"`
        `"nightreport <location_name>/<camera_name>"`
        `"channel <location_name>/<camera_name>/<channel_name>"`

    A confirmation `"OK <location_name>/<camera_name>[/<channel_name>]"`
    will be returned, followed by updates for the chosen service.

    Parameters
    ----------
    websocket : WebSocket
        The websocket object representing the server/client connection.
    """
    await websocket.accept()
    try:
        while True:
            data: str = await websocket.receive_text()
            text = data.strip()
            if not is_valid_client_request(text):
                continue
            updater, loc_cam_id = text.split(" ")
            location, camera, *channel = loc_cam_id.split("/")
            locations = websocket.app.state.models.locations
            if not is_valid_location_camera(location, camera, locations):
                continue
            match updater:
                case "camera":
                    await websocket.send_text(f"OK {loc_cam_id}")
                    connected_clients[websocket] = (updater, loc_cam_id)
    except WebSocketDisconnect:
        if websocket in connected_clients:
            del connected_clients[websocket]


async def notify_camera_clients(
    message_for_cam: dict[str, list[Event] | None]
) -> None:
    ((msg_cam_loc, events),) = message_for_cam.items()
    for websocket, (updater, loc_cam_id) in connected_clients.items():
        if updater == "camera" and loc_cam_id == msg_cam_loc:
            if events:
                serialised = [ev.__dict__ for ev in events]
            else:
                serialised = None
            await websocket.send_json(serialised)
    return


def is_valid_client_request(client_text: str) -> bool:
    valid_req = re.compile(r"^(camera|channel|nightreport)\s+[\w\/]+\w+$")
    if valid_req.fullmatch(client_text):
        return True
    return False


def is_valid_location_camera(
    location_name: str, camera_name: str, locations: list[Location]
) -> bool:
    location: Location | None
    if not (location := find_first(locations, "name", location_name)):
        return False
    camera: Camera | None
    if not (camera := find_first(location.cameras, "name", camera_name)):
        return False
    if not camera.online:
        return False
    return True
