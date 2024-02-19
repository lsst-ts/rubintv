import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.models.models import Camera, Event, Location
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator
from lsst.ts.rubintv.tests.mockdata import mock_up_data
from moto import mock_s3

m = ModelsInitiator()


@pytest.fixture(scope="function")
def setup_mock_s3_environment(mock_s3_client: Any) -> Any:
    with mock_s3():
        mock_up_data(m.locations)
        yield


@pytest.fixture
def current_poller(setup_mock_s3_environment: Any) -> CurrentPoller:
    return CurrentPoller(m.locations)


@pytest.fixture
def c_poller_no_mock_data(mock_s3_client: Any) -> Any:
    with mock_s3():
        yield CurrentPoller(m.locations)


@pytest.mark.asyncio
async def test_poll_buckets_for_todays_data(
    current_poller: CurrentPoller,
) -> None:
    # Mocking external functions
    with patch(
        "lsst.ts.rubintv.models.models.get_current_day_obs", return_value="20210101"
    ) as mock_day_obs, patch(
        "lsst.ts.rubintv.background.currentpoller.CurrentPoller.clear_all_data",
        new_callable=AsyncMock,
    ), patch(
        "lsst.ts.rubintv.background.currentpoller.CurrentPoller.seive_out_metadata",
        new_callable=AsyncMock,
    ) as mock_metadata, patch(
        (
            "lsst.ts.rubintv.background.currentpoller.CurrentPoller."
            "seive_out_night_reports"
        ),
        new_callable=AsyncMock,
    ) as mock_night_reports, patch(
        "lsst.ts.rubintv.background.currentpoller.CurrentPoller."
        "process_channel_objects",
        new_callable=AsyncMock,
    ) as mock_process_objects:
        # Execute test
        try:
            # Run the method for a specified number of seconds, then timeout
            await asyncio.wait_for(
                current_poller.poll_buckets_for_todays_data(), timeout=0.1
            )
        except asyncio.TimeoutError:
            pass

        # Assertions
        assert mock_day_obs
        mock_metadata.assert_called()
        mock_night_reports.assert_called()
        mock_process_objects.assert_called()
        assert current_poller.completed_first_poll is True


@pytest.mark.asyncio
async def test_poll_buckets_for_today_process_and_store_seq_events(
    current_poller: CurrentPoller,
) -> None:
    try:
        await asyncio.wait_for(
            current_poller.poll_buckets_for_todays_data(), timeout=0.1
        )
    except asyncio.TimeoutError:
        # The timeout error is expected
        pass

    mocked_events = {}
    for loc in m.locations:
        for cam in loc.cameras:
            if not cam.online:
                continue
            len_data = len(cam.channels) * 3
            if len_data > 0:
                mocked_events[f"{loc.name}/{cam.name}"] = len_data

    # make sure the keys for the location/cameras match up
    current_keys = sorted([k for k in current_poller._events.keys()])
    assert current_keys == sorted(mocked_events.keys())

    # and that they have the right number of events
    for ck in current_keys:
        assert len(current_poller._events[ck]) == mocked_events[ck]

    # print(current_poller._metadata)
    # print(current_poller._table)
    # print(current_poller._per_day)
    # print(current_poller._singles)
    # print(current_poller._nr_reports)
    # print(current_poller._nr_reports)


@pytest.mark.asyncio
async def test_clear_all_data(current_poller: CurrentPoller) -> None:
    try:
        await asyncio.wait_for(
            current_poller.poll_buckets_for_todays_data(), timeout=0.1
        )
    except asyncio.TimeoutError:
        pass
    await current_poller.clear_all_data()
    assert current_poller._objects == {}
    assert current_poller._events == {}
    assert current_poller._metadata == {}
    assert current_poller._table == {}
    assert current_poller._per_day == {}
    assert current_poller._singles == {}
    assert current_poller._nr_metadata == {}
    assert current_poller._nr_reports == {}


@pytest.mark.asyncio
async def test_process_channel_objects(
    c_poller_no_mock_data: CurrentPoller,
) -> None:
    current_poller = c_poller_no_mock_data
    location: Location = find_first(m.locations, "name", "base-usdf")
    # fake_auxtel has both 'streaming' and per-day channels
    camera: Camera = find_first(location.cameras, "name", "fake_auxtel")

    iterations = 1
    objects = []
    for channel in camera.channels:
        for index in range(iterations):
            seq_num = f"{index:06}"
            objects.append(
                {
                    "key": f"{camera.name}/2022-11-22/{channel.name}/"
                    f"{seq_num}/test.test",
                    "hash": "",
                }
            )

    mock_event_list = [
        Event(
            key="fake_auxtel/2022-11-22/test/000000/test.test",
            hash="",
            camera_name="fake_auxtel",
            day_obs="2022-11-22",
            channel_name="monitor",
            seq_num="000000",
            filename="test.test",
            ext="test",
        )
    ]

    with (
        patch(
            "lsst.ts.rubintv.background.currentpoller.CurrentPoller."
            "update_channel_events",
            new_callable=AsyncMock,
        ) as mock_update_channel_events,
        patch(
            "lsst.ts.rubintv.background.currentpoller.CurrentPoller.make_per_day_data",
            return_value=mock_event_list,
            new_callable=AsyncMock,
        ) as mock_make_per_day_data,
    ):
        await current_poller.process_channel_objects(
            objects, f"{location.name}/{camera.name}", camera
        )

        expected_events = []
        for chan in camera.channels:
            expected_events.append(
                Event(
                    key=f"fake_auxtel/2022-11-22/{chan.name}/000000/test.test",
                    hash="",
                    camera_name="fake_auxtel",
                    day_obs="2022-11-22",
                    channel_name=chan.name,
                    seq_num="000000",
                    filename="test.test",
                    ext="test",
                )
            )
        mock_update_channel_events.assert_called_once_with(
            expected_events, camera, "base-usdf/fake_auxtel"
        )
        mock_make_per_day_data.assert_called()
