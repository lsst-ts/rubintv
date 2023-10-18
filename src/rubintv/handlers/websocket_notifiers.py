from typing import Any, Mapping, Tuple
from uuid import UUID

from rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
)
from rubintv.models.models import (
    Event,
    NightReportPayload,
    get_current_day_obs,
)


async def notify_camera_events_update(
    message_for_cam: Tuple[str, list[Event]]
) -> None:
    """Receives and processes messages to pass on to connected clients.


    Parameters
    ----------
    message_for_cam : `Tuple` [`str`, `dict` [`list` [`Event`]]]
        Messages take the form: {f"{location_name}/{camera_name}": payload}
        where payload is a dict of list of events, keyed by channel name.
    """
    service = "camera"
    loc_cam, events_list = message_for_cam
    service_loc_cam_chan = " ".join([service, loc_cam])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    events_dict: dict[str, list[dict[str, Any]]] = {}
    for e in events_list:
        if e.channel_name in events_dict:
            events_dict[e.channel_name].append(e.__dict__)
        else:
            events_dict[e.channel_name] = [e.__dict__]
    await notify_clients(to_notify, "channelData", events_dict)


async def notify_camera_metadata_update(
    message_for_cam: Tuple[str, dict]
) -> None:
    """Receives and processes messages to pass on to connected clients.


    Parameters
    ----------
    message_for_cam :  `Tuple` [`str`, `dict`]
        Messages take the form: {f"{location_name}/{camera_name}": payload}
        where payload is either a list of channel-related events or a single
        dict of metadata.
    """
    service = "camera"
    loc_cam, metadata = message_for_cam
    service_loc_cam_chan = " ".join([service, loc_cam])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    await notify_clients(to_notify, "metadata", metadata)


async def notify_channel_update(message_for_chan: Tuple[str, Event]) -> None:
    service = "channel"
    loc_cam_chan, event = message_for_chan
    service_loc_cam_chan = " ".join([service, loc_cam_chan])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    await notify_clients(to_notify, "event", event.__dict__)


async def notify_night_report_update(
    message: Tuple[str, NightReportPayload]
) -> None:
    service = "nightreport"
    loc_cam, night_report = message
    service_loc_cam_chan = " ".join([service, loc_cam])
    to_notify = await get_clients_to_notify(service_loc_cam_chan)
    await notify_clients(to_notify, "nightReport", night_report)


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


# async def notify_of_status(client_id: UUID, historical_busy: bool) -> None:
