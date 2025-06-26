from datetime import timedelta
from typing import Any, Iterator
from unittest.mock import AsyncMock, call, patch

import pytest
from botocore.exceptions import ClientError
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.models.models import Camera, Location, NightReport
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..conftest import mock_s3_service
from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.fixture(scope="function")
def rubin_data_mocker(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        mocker = RubinDataMocker(m.locations, s3_required=True)
        yield mocker


@pytest.fixture(scope="function")
def empty_mocker(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        # Clear any residual data
        for location in m.locations:
            bucket_name = location.bucket_name
            try:
                objects = mock_s3_client.list_objects(Bucket=bucket_name).get(
                    "Contents", []
                )
                for obj in objects:
                    mock_s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            except ClientError:
                pass

        # Initialize RubinDataMocker
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        yield mocker


@pytest.fixture
def current_poller(rubin_data_mocker: RubinDataMocker) -> CurrentPoller:
    return CurrentPoller(m.locations, test_mode=True)


rtv_root = "lsst.ts.rubintv"
cp_path = f"{rtv_root}.background.currentpoller.CurrentPoller"


@pytest.mark.asyncio
@patch(f"{cp_path}.sieve_out_metadata", new_callable=AsyncMock)
@patch(f"{cp_path}.sieve_out_night_reports", new_callable=AsyncMock)
@patch(f"{cp_path}.process_channel_objects", new_callable=AsyncMock)
@patch(f"{cp_path}.poll_for_yesterdays_per_day", new_callable=AsyncMock)
async def test_poll_buckets_for_todays_data(
    mock_poll_for_yesterdays_per_day: AsyncMock,
    mock_process_objects: AsyncMock,
    mock_night_reports: AsyncMock,
    mock_sieve_out_metadata: AsyncMock,
    current_poller: CurrentPoller,
) -> None:
    # Configure AsyncMock to behave as awaited coroutines
    mock_sieve_out_metadata.return_value = None
    mock_night_reports.return_value = None
    mock_process_objects.return_value = None
    mock_poll_for_yesterdays_per_day.return_value = None

    # Execute test

    await current_poller.poll_buckets_for_todays_data()

    # Assertions
    mock_sieve_out_metadata.assert_called()
    mock_night_reports.assert_called()
    mock_process_objects.assert_called()
    mock_poll_for_yesterdays_per_day.assert_called()
    assert current_poller.completed_first_poll is True


@pytest.mark.asyncio
async def test_poll_buckets_for_today_process_and_store_seq_events(
    current_poller: CurrentPoller, rubin_data_mocker: RubinDataMocker
) -> None:
    await current_poller.poll_buckets_for_todays_data()

    mocked_objs_keys = rubin_data_mocker.events.keys()

    # make sure the keys for the location/cameras match up
    current_keys = sorted([k for k in current_poller._events.keys()])
    assert current_keys == sorted(mocked_objs_keys)

    # and that they have the right number of events
    for ck in current_keys:
        assert sorted(current_poller._events[ck]) == sorted(
            rubin_data_mocker.events[ck]
        )


@pytest.mark.asyncio
async def test_clear_todays_data(current_poller: CurrentPoller) -> None:
    await current_poller.poll_buckets_for_todays_data()

    assert current_poller.completed_first_poll is True
    assert current_poller._objects != {}

    await current_poller.clear_todays_data()
    assert current_poller._objects == {}
    assert current_poller._events == {}
    assert current_poller._metadata == {}
    assert current_poller._table == {}
    assert current_poller._per_day == {}
    assert current_poller._most_recent_events == {}
    assert current_poller._nr_metadata == {}
    assert current_poller._night_reports == {}


@patch(f"{rtv_root}.background.currentpoller.notify_ws_clients", new_callable=AsyncMock)
@patch(f"{cp_path}.make_per_day_data", new_callable=AsyncMock)
@patch(f"{cp_path}.update_channel_events", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_process_channel_objects(
    mock_update_channel_events: AsyncMock,
    mock_make_per_day_data: AsyncMock,
    mock_notify_ws_clients: AsyncMock,
    current_poller: CurrentPoller,
    rubin_data_mocker: RubinDataMocker,
) -> None:
    # Test setup
    camera, location = get_test_camera_and_location()
    loc_cam = f"{location.name}/{camera.name}"
    objects = rubin_data_mocker.seq_objs[loc_cam]

    # Call the method under test
    await current_poller.process_channel_objects(objects, location, camera)

    # Expected events
    expected_events = rubin_data_mocker.events[loc_cam]

    # Assertions
    mock_update_channel_events.assert_called_once_with(
        expected_events, location, camera
    )
    mock_make_per_day_data.assert_called()
    mock_notify_ws_clients.assert_called()


@patch(f"{rtv_root}.background.currentpoller.notify_ws_clients", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_update_channel_events(
    mock_notify_ws_clients: AsyncMock,
    current_poller: CurrentPoller,
    rubin_data_mocker: RubinDataMocker,
) -> None:
    camera, location = get_test_camera_and_location()
    loc_cam = f"{location.name}/{camera.name}"
    events = rubin_data_mocker.events[loc_cam]

    await current_poller.clear_todays_data()
    assert current_poller._most_recent_events == {}
    await current_poller.update_channel_events(events, location, camera)
    assert current_poller._most_recent_events != {}
    mock_notify_ws_clients.assert_called()


@pytest.mark.asyncio
async def test_make_per_day_data(
    current_poller: CurrentPoller, rubin_data_mocker: RubinDataMocker
) -> None:
    mocked_events = rubin_data_mocker.events
    for location in m.locations:
        for camera in location.cameras:
            if not camera.online:
                continue
            loc_cam = f"{location.name}/{camera.name}"
            events = mocked_events[loc_cam]
            pd_data = await current_poller.make_per_day_data(camera, events)
            pd_chan_names = [chan.name for chan in camera.pd_channels()]
            if not pd_chan_names:
                assert pd_data == {}
            else:
                expected = {}
                for name in pd_chan_names:
                    s_events = sorted(
                        [ev for ev in events if ev.channel_name == name],
                        key=lambda ev: ev.seq_num_force_int(),
                    )
                    last_event = s_events.pop()
                    expected[name] = last_event.__dict__
                assert pd_data == expected


@pytest.mark.asyncio
@patch(f"{rtv_root}.background.currentpoller.get_current_day_obs", autospec=True)
@patch(f"{cp_path}.clear_todays_data", new_callable=AsyncMock)
async def test_day_rollover(
    mock_clear_data: AsyncMock,
    mock_get_current_day_obs: AsyncMock,
    current_poller: CurrentPoller,
    rubin_data_mocker: RubinDataMocker,
) -> None:
    # Set up the initial day_obs
    day_obs = get_current_day_obs()
    mock_get_current_day_obs.return_value = day_obs

    # Perform the first poll
    await current_poller.poll_buckets_for_todays_data()
    assert current_poller.completed_first_poll is True

    # Roll over to the next day
    day_obs = day_obs + timedelta(days=1)
    rubin_data_mocker.day_obs = day_obs
    rubin_data_mocker.mock_up_data()
    mock_get_current_day_obs.return_value = day_obs

    # Perform polling for the new day
    await current_poller.poll_buckets_for_todays_data()

    # Assert that the clear_todays_data method was called twice
    mock_clear_data.assert_called_once()


@patch(f"{rtv_root}.background.currentpoller.get_current_day_obs", autospec=True)
@patch(f"{rtv_root}.background.currentpoller.notify_ws_clients", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_pick_up_yesterdays_movie(
    mock_notify_ws_clients: AsyncMock,
    mock_get_current_day_obs: AsyncMock,
    current_poller: CurrentPoller,
    rubin_data_mocker: RubinDataMocker,
) -> None:
    camera, location = get_test_camera_and_location()
    channel = camera.pd_channels()[0]
    mocked = rubin_data_mocker
    day_obs = get_current_day_obs()
    mock_get_current_day_obs.return_value = day_obs

    await current_poller.poll_buckets_for_todays_data()
    assert current_poller.completed_first_poll is True

    # clear movie channel
    mocked.delete_channel_events(location, camera, channel)
    await current_poller.poll_buckets_for_todays_data()

    # rollover day obs
    yesterday = day_obs
    day_obs = day_obs + timedelta(days=1)
    mock_get_current_day_obs.return_value = day_obs

    await current_poller.poll_buckets_for_todays_data()
    assert current_poller._events == {}

    # add movie data (arbitrary number of objs)
    mocked.add_seq_objs_for_channel(location, camera, channel, 3)
    # clear any calls made to notify clients before now
    mock_notify_ws_clients.reset_mock()

    await current_poller.poll_buckets_for_todays_data()

    events = mocked.get_mocked_events(location, camera, channel)
    assert events is not []
    last_event = max(events)
    assert last_event
    assert last_event.day_obs == yesterday.isoformat()

    # assert that notification was made with the new event
    # from yesterday.
    service_type = Service.CAMERA
    message_type = MessageType.CAMERA_PD_BACKDATED
    loc_cam = f"{location.name}/{camera.name}"
    payload = {channel.name: last_event.__dict__}
    mock_notify_ws_clients.assert_called_once_with(
        service_type, message_type, loc_cam, payload
    )


@patch(f"{rtv_root}.background.currentpoller.get_current_day_obs", autospec=True)
@patch(f"{rtv_root}.background.currentpoller.notify_ws_clients", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_notify_new_night_report_plot(
    mock_notify_ws_clients: AsyncMock,
    mock_get_current_day_obs: AsyncMock,
    current_poller: CurrentPoller,
    empty_mocker: RubinDataMocker,
) -> None:

    camera, location = get_test_camera_and_location()
    loc_cam = f"{location.name}/{camera.name}"

    mocked = empty_mocker

    # Define mock plots with the same name but different hashes
    first_plot = mocked.mock_night_report_plot(location, camera)

    # First poll
    day_obs = get_current_day_obs()
    mock_get_current_day_obs.return_value = day_obs

    await current_poller.poll_buckets_for_todays_data()

    # Assert notify_ws_clients called with the first plot
    # It's actually called twice as the first time is to
    # notify that there is a new Night Report
    assert mock_notify_ws_clients.call_count == 2
    calls = mock_notify_ws_clients.call_args_list
    print(calls[1])
    assert calls[1] == call(
        Service.NIGHTREPORT,
        MessageType.NIGHT_REPORT,
        loc_cam,
        NightReport(text={}, plots=[first_plot]).model_dump(),
    )

    second_plot = mocked.mock_night_report_plot(location, camera)

    # Reset mock_notify_ws_clients for the second poll
    mock_notify_ws_clients.reset_mock()

    # Second poll
    await current_poller.poll_buckets_for_todays_data()

    # Assert notify_ws_clients called with the second plot
    # It's only called once as the table has already been
    # notified that a Night Report exists (to display the link)
    mock_notify_ws_clients.assert_called_once_with(
        Service.NIGHTREPORT,
        MessageType.NIGHT_REPORT,
        loc_cam,
        NightReport(text={}, plots=[second_plot]).model_dump(),
    )


def get_test_camera_and_location() -> tuple[Camera, Location]:
    location: Location = find_first(m.locations, "name", "summit-usdf")
    # fake_auxtel has both 'streaming' and per-day channels
    camera: Camera = find_first(location.cameras, "name", "auxtel")
    return (camera, location)
