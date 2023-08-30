import re
from typing import Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Event, Location

ws_router = APIRouter()
connected_clients: dict[WebSocket, Tuple[str, str]] = {}


@ws_router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
) -> None:
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
            updater, loc_cam = text.split(" ")
            location, camera_name, *extra = loc_cam.split("/")

            locations = websocket.app.state.models.locations
            if not (
                camera := is_valid_location_camera(
                    location, camera_name, locations
                )
            ):
                continue

            if extra:
                channel = extra[0]
                if not is_valid_channel(camera, channel):
                    continue
            match updater:
                case "camera":
                    await websocket.send_text(f"OK {loc_cam}")
                    connected_clients[websocket] = (updater, loc_cam)
                case "channel":
                    loc_cam_chan = f"{location}/{camera_name}/{channel}"
                    await websocket.send_text(f"OK {loc_cam_chan}")
                    connected_clients[websocket] = (updater, loc_cam_chan)
    except WebSocketDisconnect:
        if websocket in connected_clients:
            del connected_clients[websocket]


async def notify_camera_update(
    message_for_cam: Tuple[str, list[Event] | None] | Tuple[str, dict | None]
) -> None:
    """Receives and processes messages to pass on to connected clients.


    Parameters
    ----------
    message_for_cam : `Tuple` [`str`, `list` [`Event`]  |  `None`] | `Tuple`
    [`str`, `dict`  |  `None`]
        Messages take the form: {f"{location_name}/{camera_name}": payload}
        where payload is either a list of channel-related events or a single
        dict of metadata.
    """
    loc_cam, events = message_for_cam
    for websocket, (to_update, loc_cam_id) in connected_clients.items():
        if to_update == "camera" and loc_cam_id == loc_cam:
            if events:
                # events can either be a list of channel events or a metadata
                # dict
                serialised: list | dict | None
                if isinstance(events, list):
                    serialised = [ev.__dict__ for ev in events]
                else:
                    serialised = events
            else:
                serialised = None
            await websocket.send_json(serialised)


async def notify_channel_update(message_for_chan: Tuple[str, Event]) -> None:
    loc_cam_chan, event = message_for_chan
    for websocket, (to_update, loc_cam_chan_id) in connected_clients.items():
        if to_update == "camera" and loc_cam_chan_id == loc_cam_chan:
            await websocket.send_json(event.__dict__)
    return


def is_valid_client_request(client_text: str) -> bool:
    valid_req = re.compile(r"^(camera|channel|nightreport)\s+[\w\/]+\w+$")
    if valid_req.fullmatch(client_text):
        return True
    return False


def is_valid_location_camera(
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


def is_valid_channel(camera: Camera, channel_name: str) -> bool:
    return camera.channels is not None and channel_name in [
        chan.name for chan in camera.channels
    ]
