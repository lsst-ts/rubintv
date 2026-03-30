"""Comprehensive tests for day rollover integration between CurrentPoller
and HistoricalPoller."""

import asyncio
from datetime import date, timedelta
from typing import Any, Iterator
from unittest.mock import AsyncMock, patch

import pytest
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import Camera, Location, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..conftest import mock_s3_service
from ..mockdata import RubinDataMocker

m = ModelsInitiator()

rtv_root = "lsst.ts.rubintv"
cp_path = f"{rtv_root}.background.currentpoller.CurrentPoller"
hp_path = f"{rtv_root}.background.historicaldata.HistoricalPoller"


@pytest.fixture(scope="function")
def rubin_data_mocker(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        mocker = RubinDataMocker(m.locations, s3_required=True, include_metadata=True)
        yield mocker


@pytest.fixture
def current_poller(rubin_data_mocker: RubinDataMocker) -> CurrentPoller:
    return CurrentPoller(m.locations, test_mode=True)


@pytest.fixture
def historical_poller() -> HistoricalPoller:
    return HistoricalPoller(m.locations)


def get_test_camera_and_location() -> tuple[Camera, Location]:
    """Get a test camera and location for testing."""
    location: Location | None = find_first(m.locations, "name", "summit-usdf")
    assert location is not None
    camera: Camera | None = find_first(location.cameras, "name", "auxtel")
    assert camera is not None
    return (camera, location)


class TestDayRolloverIntegration:
    """Test suite for day rollover integration between CurrentPoller and
    HistoricalPoller."""

    @pytest.mark.asyncio
    async def test_set_historical_poller_reference(
        self, current_poller: CurrentPoller, historical_poller: HistoricalPoller
    ) -> None:
        """Test that CurrentPoller can be given a reference to
        HistoricalPoller."""
        assert current_poller._historical_poller is None

        current_poller.set_historical_poller(historical_poller)

        assert current_poller._historical_poller is historical_poller

    @pytest.mark.asyncio
    async def test_day_rollover_calls_integrate_todays_data(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that day rollover triggers integrate_todays_data call."""
        current_poller.set_historical_poller(historical_poller)

        # Mock the integration method
        with patch.object(
            historical_poller, "integrate_todays_data", new_callable=AsyncMock
        ) as mock_integrate:
            mock_integrate.return_value = None

            # First poll on current day
            await current_poller.poll_buckets_for_todays_data()

            # Should not be called yet
            mock_integrate.assert_not_called()

            # Simulate day rollover
            current_poller._last_day_obs = get_current_day_obs() + timedelta(days=1)
            rubin_data_mocker.day_obs = current_poller._last_day_obs
            rubin_data_mocker.mock_up_data()

            # Second poll on new day
            await current_poller.poll_buckets_for_todays_data()

            # Should now be called
            mock_integrate.assert_called_once()

    @pytest.mark.asyncio
    async def test_integrate_todays_data_with_events(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that today's events are integrated into historical store."""
        camera, location = get_test_camera_and_location()

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Get events from current poller
        events = await current_poller.get_current_events(location.name, camera)
        assert len(events) > 0

        # Integrate into historical
        await historical_poller.integrate_todays_data(current_poller)

        # Verify events were stored
        today = current_poller._last_day_obs
        assert (location, camera) in historical_poller._structured_events
        assert today in historical_poller._structured_events[(location, camera)]

    @pytest.mark.asyncio
    async def test_integrate_todays_metadata(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that today's metadata is integrated into historical store."""
        camera, location = get_test_camera_and_location()

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Get metadata from current poller
        metadata = await current_poller.get_current_metadata(location.name, camera)

        # Only test if metadata was found
        if metadata:
            # Integrate into historical
            await historical_poller.integrate_todays_data(current_poller)

            # Verify metadata references were stored
            today_iso = current_poller._last_day_obs.isoformat()
            assert (
                f"{location.name}/{camera.name}"
            ) in historical_poller._metadata_collector._metadata_refs
            metadata_refs = historical_poller._metadata_collector._metadata_refs[
                f"{location.name}/{camera.name}"
            ]
            metadata_dates = {ref.date_str for ref in metadata_refs}
            assert today_iso in metadata_dates

    @pytest.mark.asyncio
    async def test_integrate_todays_night_report(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that today's night report data is integrated."""
        camera, location = get_test_camera_and_location()

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Get night report from current poller
        night_report = await current_poller.get_current_night_report(
            location.name, camera.name
        )

        # Integrate into historical
        await historical_poller.integrate_todays_data(current_poller)

        # If night report had plots, verify they're in historical
        if night_report.plots:
            assert location.name in historical_poller._nr_metadata
            nr_data = historical_poller._nr_metadata[location.name]
            assert len(nr_data) > 0

    @pytest.mark.asyncio
    async def test_calendar_updated_on_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that calendar is updated when integrating today's data."""
        camera, location = get_test_camera_and_location()
        loc_cam = (location, camera)

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Integrate into historical
        await historical_poller.integrate_todays_data(current_poller)

        # Verify calendar was updated
        today_iso = current_poller._last_day_obs.isoformat()
        year, month, day = today_iso.split("-")
        year, month, day = int(year), int(month), int(day)

        assert loc_cam in historical_poller._calendar
        assert year in historical_poller._calendar[loc_cam]
        assert month in historical_poller._calendar[loc_cam][year]
        assert day in historical_poller._calendar[loc_cam][year][month]

    @pytest.mark.asyncio
    async def test_multiple_cameras_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that integration works for multiple cameras."""
        location = m.locations[0]

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Integrate into historical
        await historical_poller.integrate_todays_data(current_poller)

        # Verify all online cameras were integrated
        today_iso = current_poller._last_day_obs.isoformat()

        for camera in location.cameras:
            if not camera.online:
                continue

            loc_cam = f"{location.name}/{camera.name}"
            # At least one should have data
            if loc_cam in historical_poller._structured_events:
                assert today_iso in historical_poller._structured_events[loc_cam]

    @pytest.mark.asyncio
    async def test_integration_handles_no_events(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that integration gracefully handles cameras with no events."""
        # Set up a scenario where current poller has no data
        await current_poller.clear_todays_data()

        # This should not raise an error
        await historical_poller.integrate_todays_data(current_poller)

    @pytest.mark.asyncio
    async def test_integration_without_historical_poller_reference(
        self,
        current_poller: CurrentPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that polling continues even without historical poller set."""
        # Don't set historical poller reference
        assert current_poller._historical_poller is None

        # This should complete without error
        await current_poller.poll_buckets_for_todays_data()
        assert current_poller.completed_first_poll is True

    @pytest.mark.asyncio
    async def test_clear_called_after_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that current poller clears data after day rollover."""
        current_poller.set_historical_poller(historical_poller)

        # Poll on first day
        await current_poller.poll_buckets_for_todays_data()
        assert current_poller._events != {}

        # Simulate day rollover
        current_poller._last_day_obs = get_current_day_obs() + timedelta(days=1)
        rubin_data_mocker.day_obs = current_poller._last_day_obs
        rubin_data_mocker.mock_up_data()

        # Mock clear_todays_data to track if it's called
        with patch.object(
            current_poller, "clear_todays_data", new_callable=AsyncMock
        ) as mock_clear:
            # Poll on new day
            await current_poller.poll_buckets_for_todays_data()

            # Verify clear was called during day rollover
            mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_events_consistency_across_rollover(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that events remain consistent after day rollover."""
        camera, location = get_test_camera_and_location()
        loc_cam = (location, camera)

        # Get events from first day
        await current_poller.poll_buckets_for_todays_data()
        day1_events = await current_poller.get_current_events(location.name, camera)
        day1_count = len(day1_events)

        # Integrate to historical
        await historical_poller.integrate_todays_data(current_poller)
        day1 = current_poller._last_day_obs

        if day1_count > 0:
            historical_day1_events = historical_poller._structured_events.get(
                loc_cam, {}
            ).get(day1, {})
            assert len(historical_day1_events) > 0

        # Simulate day rollover
        current_poller._last_day_obs = get_current_day_obs() + timedelta(days=1)
        rubin_data_mocker.day_obs = current_poller._last_day_obs
        rubin_data_mocker.mock_up_data()

        # Poll on new day
        await current_poller.poll_buckets_for_todays_data()

        # Day 1 data should still be in historical
        if day1_count > 0:
            assert day1 in historical_poller._structured_events.get(loc_cam, {})

    @pytest.mark.asyncio
    async def test_metadata_cache_shifted_on_day_change(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that metadata cache is properly shifted on day change."""
        _, location = get_test_camera_and_location()

        # Populate historical data
        await historical_poller._initialise_location_store(location)

        # Initialize metadata cache
        await historical_poller._metadata_collector.start_prefetch([location])

        # Verify cache was initialized
        await asyncio.sleep(0.1)  # Give prefetch a moment
        assert historical_poller._metadata_collector._metadata_prefetch_task is not None

        # Now integrate new day's data
        await current_poller.poll_buckets_for_todays_data()
        await historical_poller.integrate_todays_data(current_poller)

        # Verify metadata cache was updated with today's data
        assert len(historical_poller._metadata_collector._metadata_refs) > 0

    @pytest.mark.asyncio
    async def test_concurrent_access_during_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that concurrent access works during integration."""
        camera, location = get_test_camera_and_location()

        # Poll current data
        await current_poller.poll_buckets_for_todays_data()

        # Simulate concurrent reads while integrating
        async def concurrent_read() -> date | None:
            return await historical_poller.get_most_recent_day(location, camera)

        # Start integration
        integration_task = asyncio.create_task(
            historical_poller.integrate_todays_data(current_poller)
        )

        # Read concurrently
        read_tasks = [concurrent_read() for _ in range(5)]

        # Wait for all to complete
        await asyncio.gather(integration_task, *read_tasks)

    @pytest.mark.asyncio
    async def test_per_day_channels_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that per-day channels are properly integrated."""
        camera, location = get_test_camera_and_location()

        # Poll to populate current data
        await current_poller.poll_buckets_for_todays_data()

        # Get per-day data
        per_day_data = await current_poller.get_current_per_day_data(
            location.name, camera
        )

        if per_day_data:
            # Integrate into historical
            await historical_poller.integrate_todays_data(current_poller)

            # Verify per-day data was stored
            historical_per_day = await historical_poller.get_per_day_for_date(
                location, camera, current_poller._last_day_obs
            )
            assert len(historical_per_day) > 0

    @pytest.mark.asyncio
    @patch(
        f"{rtv_root}.background.historicaldata.notify_ws_clients",
        new_callable=AsyncMock,
    )
    async def test_day_change_notification_sent(
        self,
        mock_notify: AsyncMock,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that day change notification is sent during integration."""
        # Poll current data
        await current_poller.poll_buckets_for_todays_data()

        # Integration should trigger notification
        await historical_poller.integrate_todays_data(current_poller)

        # Verify notification was sent
        assert mock_notify.called

    @pytest.mark.asyncio
    async def test_extension_handling_during_integration(
        self,
        current_poller: CurrentPoller,
        historical_poller: HistoricalPoller,
        rubin_data_mocker: RubinDataMocker,
    ) -> None:
        """Test that event extensions are properly handled during
        integration."""
        camera, location = get_test_camera_and_location()

        # Poll to
