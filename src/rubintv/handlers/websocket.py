from asyncio import sleep

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from rubintv.handlers.websocket_helpers import (
    is_valid_channel,
    is_valid_client_request,
    is_valid_location_camera,
)
from rubintv.handlers.websockets_clients import (
    connected_clients,
    status_clients,
)

ws_router = APIRouter()


@ws_router.websocket("/")
async def data_websocket(
    websocket: WebSocket,
) -> None:
    """Websocket endpoint for providing updates for camera data, channels or
    night reports services.

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
            if not await is_valid_client_request(text):
                continue
            service, loc_cam = text.split(" ")
            location, camera_name, *extra = loc_cam.split("/")

            locations = websocket.app.state.models.locations
            if not (
                camera := await is_valid_location_camera(
                    location, camera_name, locations
                )
            ):
                continue

            if extra:
                channel = extra[0]
                if not await is_valid_channel(camera, channel):
                    continue
            match service:
                case "camera":
                    await websocket.send_text(f"OK/{loc_cam}")
                    connected_clients[websocket] = (service, loc_cam)
                case "channel":
                    loc_cam_chan = f"{location}/{camera_name}/{channel}"
                    await websocket.send_text(f"OK/{loc_cam_chan}")
                    connected_clients[websocket] = (service, loc_cam_chan)
                case "nightreport":
                    await websocket.send_text(f"OK/Night Report {loc_cam}")
                    connected_clients[websocket] = (service, loc_cam_chan)
    except WebSocketDisconnect:
        if websocket in connected_clients:
            del connected_clients[websocket]


@ws_router.websocket("/status")
async def status_websocket(websocket: WebSocket) -> None:
    """Websocket connection to provide info about the status of the app.

    Parameters
    ----------
    websocket : WebSocket
        The websocket for requesting/supplying status data.
    """
    await websocket.accept()
    status_clients.append(websocket)
    try:
        while True:
            await sleep(7)
    except WebSocketDisconnect:
        if websocket in status_clients:
            status_clients.remove(websocket)
