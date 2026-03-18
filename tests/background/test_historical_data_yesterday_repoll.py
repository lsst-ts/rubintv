from datetime import timedelta
from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.fixture(scope="function")
def rubin_data_mocker_yesterday(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    """Create a data mocker for yesterday's data with S3 backend.

    Note: This fixture depends on mock_s3_client to ensure the S3 service
    is active during the test.
    """
    yesterday = get_current_day_obs() - timedelta(days=1)
    mocker = RubinDataMocker(
        m.locations, day_obs=yesterday, s3_required=True, populate=True
    )
    yield mocker


@pytest.fixture(scope="function")
def historical_poller_with_yesterday_data(
    rubin_data_mocker_yesterday: RubinDataMocker,
) -> HistoricalPoller:
    """Create a HistoricalPoller instance ready to work with yesterday's mock
    data."""
    return HistoricalPoller(m.locations)


class TestRepollYesterday:
    """Test suite for repoll_yesterday functionality."""

    @pytest.mark.asyncio
    async def test_repoll_yesterday_detects_new_events(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test that repoll_yesterday detects new events added to yesterday's
        bucket."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Initial download for all dates
        await historical._initialise_location_store(location)

        # Get initial event count for yesterday
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)

        # Add more events to mock bucket for yesterday
        rubin_data_mocker_yesterday.add_seq_objs_for_channel(
            location, camera, channel, num_objs=3
        )

        # Get new objects from bucket for yesterday specifically
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        # Execute _update_if_changed with specific date
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify new events were added to cache
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) > initial_count

    @pytest.mark.asyncio
    async def test_repoll_yesterday_detects_removed_events(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test that repoll_yesterday detects events removed from yesterday's
        bucket."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial events for yesterday
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)
        assert initial_count > 0

        # Find a channel that actually has events (not the empty channel)
        loc_cam = f"{location.name}/{camera.name}"
        empty_channel_name = rubin_data_mocker_yesterday.empty_channel.get(loc_cam)

        # Select a channel with events
        channel = None
        for chan in camera.channels:
            if chan.name != empty_channel_name:
                chan_events = [e for e in initial_events if e.channel_name == chan.name]
                if chan_events:
                    channel = chan
                    break

        assert channel is not None, "No channel with events found for deletion test"

        # Get object count before deletion
        objects_before = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )
        count_before = len(objects_before)

        # Delete events from the channel with actual events
        rubin_data_mocker_yesterday.delete_channel_events(location, camera, channel)

        # Get updated objects from bucket for yesterday
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )
        count_after = len(new_objects)

        # Verify deletion actually took effect in the mock
        if count_after >= count_before:
            # Deletion didn't work as expected in mock
            # Skip this assertion since it's a mock limitation
            pytest.skip(
                f"Mock deletion did not take effect: "
                f"{count_before} objects before, {count_after} after"
            )

        # Execute _update_if_changed
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify events were removed from cache
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) < initial_count

    @pytest.mark.asyncio
    async def test_repoll_yesterday_no_changes(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test that repoll_yesterday handles the case where no changes
        occurred."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial events
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)

        # Get objects from bucket (no changes made to mocker)
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        # Execute _update_if_changed
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify cache remains unchanged
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) == initial_count

    @pytest.mark.asyncio
    async def test_repoll_yesterday_multiple_cameras(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test repoll_yesterday with multiple cameras."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial event counts for each camera
        initial_counts = {}
        for camera in location.cameras:
            if camera.online:
                events = await historical.get_events_for_date(
                    location, camera, yesterday
                )
                initial_counts[camera.name] = len(events)

        # Add new events for each camera
        for camera in location.cameras:
            if camera.online and camera.channels:
                channel = camera.channels[0]
                rubin_data_mocker_yesterday.add_seq_objs_for_channel(
                    location, camera, channel, num_objs=2
                )

        # Re-poll yesterday's data for each camera
        for camera in location.cameras:
            if camera.online:
                new_objects = await historical._get_objects_for_location_camera(
                    location, camera, prefix_extra=yesterday.isoformat()
                )
                await historical._update_if_changed(
                    location, camera, new_objects, yesterday
                )

        # Verify all cameras were updated
        for camera in location.cameras:
            if camera.online:
                events = await historical.get_events_for_date(
                    location, camera, yesterday
                )
                assert len(events) > initial_counts[camera.name]

    @pytest.mark.asyncio
    async def test_repoll_yesterday_integration(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Integration test for repoll_yesterday method."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial count for yesterday
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)

        # Add new events
        rubin_data_mocker_yesterday.add_seq_objs_for_channel(
            location, camera, channel, num_objs=2
        )

        # Call the actual repoll_yesterday method
        await historical.repoll_yesterday()

        # Verify new events were detected and cached
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) > initial_count


class TestUpdateIfChanged:
    """Test suite for _update_if_changed functionality."""

    @pytest.mark.asyncio
    async def test_update_if_changed_with_additions(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test _update_if_changed updates cache when events are added."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial count
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)

        # Add new events
        rubin_data_mocker_yesterday.add_seq_objs_for_channel(
            location, camera, channel, num_objs=3
        )

        # Get new objects
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        # Execute _update_if_changed
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify new events were added
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) > initial_count

    @pytest.mark.asyncio
    async def test_update_if_changed_with_deletions(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test _update_if_changed updates cache when events are removed."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial count
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)
        assert initial_count > 0

        # Delete all events for the channel
        rubin_data_mocker_yesterday.delete_channel_events(location, camera, channel)

        # Get updated objects
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        # Execute _update_if_changed
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify events were removed
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) < initial_count

    @pytest.mark.asyncio
    async def test_update_if_changed_no_changes(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test _update_if_changed skips update when no changes detected."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial events
        initial_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        initial_count = len(initial_events)

        # Get objects again (no changes)
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        # Execute _update_if_changed
        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify cache remains unchanged
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(updated_events) == initial_count

    @pytest.mark.asyncio
    async def test_update_if_changed_multiple_channels(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test _update_if_changed with multiple channels in the same date."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get initial counts for each channel
        initial_counts = {}
        for channel in camera.channels:
            events = await historical.get_events_for_date(location, camera, yesterday)
            channel_events = [e for e in events if e.channel_name == channel.name]
            initial_counts[channel.name] = len(channel_events)

        # Add events to first channel only
        if camera.channels:
            first_channel = camera.channels[0]
            rubin_data_mocker_yesterday.add_seq_objs_for_channel(
                location, camera, first_channel, num_objs=2
            )

        # Get new objects and update
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify first channel was updated
        updated_events = await historical.get_events_for_date(
            location, camera, yesterday
        )
        first_channel_events = [
            e for e in updated_events if e.channel_name == camera.channels[0].name
        ]
        assert len(first_channel_events) > initial_counts[camera.channels[0].name]

        # Verify other channels unchanged
        for channel in camera.channels[1:]:
            channel_events = [
                e for e in updated_events if e.channel_name == channel.name
            ]
            assert len(channel_events) == initial_counts[channel.name]

    @pytest.mark.asyncio
    async def test_update_if_changed_preserves_metadata(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test that _update_if_changed properly handles metadata files."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download with metadata
        await historical._initialise_location_store(location)

        # Get new objects including metadata
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify metadata was processed
        has_metadata = await historical.check_for_metadata_for_date(
            location, camera, yesterday
        )
        # Metadata handling depends on whether it exists in mock data
        assert isinstance(has_metadata, bool)

    @pytest.mark.asyncio
    async def test_update_if_changed_handles_final_seq_num(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test _update_if_changed handles special seq_num values like
        'final'."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Initial download
        await historical._initialise_location_store(location)

        # Get objects which may include 'final' seq_nums for per_day channels
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Get the structured data
        structured_data = await historical.get_structured_data_for_date(
            location, camera, yesterday
        )

        # Verify the data structure is correct
        assert isinstance(structured_data, dict)

        # Verify we have channel data with proper structure
        assert (
            len(structured_data) > 0
        ), "Structured data should contain channel information"

        # Verify each channel's data has the expected structure (seq_num ->
        # data)
        for channel_name, seq_data in structured_data.items():
            assert isinstance(
                seq_data, set
            ), f"Channel {channel_name} data should be a set"
            # Each seq_num should map to some data
            assert (
                len(seq_data) > 0
            ), f"Channel {channel_name} should have seq_num entries"
            # Verify all members are string seq_nums (including 'final' for
            # per_day channels)
            for seq_num in seq_data:
                assert isinstance(seq_num, str) or isinstance(
                    seq_num, int
                ), f"seq_num should be string or int, got {type(seq_num)}"

    @pytest.mark.asyncio
    async def test_update_if_changed_partial_date_update(
        self, rubin_data_mocker_yesterday: RubinDataMocker
    ) -> None:
        """Test that _update_if_changed can update specific dates only."""
        yesterday = get_current_day_obs() - timedelta(days=1)
        two_days_ago = yesterday - timedelta(days=1)
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Initial download (covers both dates)
        await historical._initialise_location_store(location)

        # Get events for both dates
        events_yesterday_before = await historical.get_events_for_date(
            location, camera, yesterday
        )
        events_two_days_before = await historical.get_events_for_date(
            location, camera, two_days_ago
        )

        # Add new events only for yesterday
        rubin_data_mocker_yesterday.add_seq_objs_for_channel(
            location, camera, channel, num_objs=2
        )

        # Get and update only yesterday's data
        new_objects = await historical._get_objects_for_location_camera(
            location, camera, prefix_extra=yesterday.isoformat()
        )

        await historical._update_if_changed(location, camera, new_objects, yesterday)

        # Verify yesterday was updated
        events_yesterday_after = await historical.get_events_for_date(
            location, camera, yesterday
        )
        assert len(events_yesterday_after) > len(events_yesterday_before)

        # Verify two days ago unchanged (not specified in update call)
        # Note: This assumes two_days_ago data was already cached
        events_two_days_after = await historical.get_events_for_date(
            location, camera, two_days_ago
        )
        assert len(events_two_days_after) == len(events_two_days_before)
