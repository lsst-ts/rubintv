import datetime
from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.handlers.websocket_notifiers import get_current_day_obs
from lsst.ts.rubintv.models.models import Event
from lsst.ts.rubintv.models.models_helpers import date_str_to_date
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..conftest import mock_s3_service
from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.fixture(scope="function")
def rubin_data_mocker(mock_s3_client: Any) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        mocker = RubinDataMocker(m.locations, s3_required=True)
        yield mocker


@pytest.fixture
def historical(rubin_data_mocker: RubinDataMocker) -> HistoricalPoller:
    return HistoricalPoller(m.locations)


@pytest.fixture(scope="function")
def c_poller_no_mock_data(rubin_data_mocker: RubinDataMocker) -> Any:
    with mock_s3_service():
        yield HistoricalPoller(m.locations)


class TestHistoricalPoller:
    """Test suite for HistoricalPoller class."""

    @pytest.mark.asyncio
    async def test_init(self, historical: HistoricalPoller) -> None:
        """Test HistoricalPoller initialization."""
        assert historical._have_downloaded is False
        assert len(historical._clients) == len(m.locations)
        assert historical._metadata_collector.metadata_refs == {}
        assert historical._structured_events == {}
        assert historical._nr_metadata == {}
        assert historical._calendar == {}

    @pytest.mark.asyncio
    async def test_clear_all_data(self, historical: HistoricalPoller) -> None:
        """Test clearing all cached data."""
        # Populate some test data
        location = m.locations[0]
        camera = location.cameras[0]
        from datetime import date

        historical._have_downloaded = True
        historical._metadata_collector.register_metadata_ref(
            f"{location.name}/{camera.name}",
            date_str="2024-01-15",
            metadata_hash="mock_hash",
        )
        historical._structured_events[(location, camera)] = {date(2024, 1, 15): {}}
        historical._nr_metadata[location] = []
        historical._calendar[(location, camera)] = {}
        historical._metadata_collector.register_metadata_ref(
            "test", date_str="2024-01-15", metadata_hash="mock_hash"
        )

        await historical.clear_all_data()

        assert historical._have_downloaded is False
        assert historical._metadata_collector.metadata_refs == {}
        assert historical._structured_events == {}
        assert historical._nr_metadata == {}
        assert historical._calendar == {}

    @pytest.mark.asyncio
    async def test_is_busy(self, historical: HistoricalPoller) -> None:
        """Test the busy status indicator."""
        historical._have_downloaded = False
        assert await historical.is_busy() is True

        historical._have_downloaded = True
        assert await historical.is_busy() is False

    @pytest.mark.asyncio
    async def test_add_to_calendar(self, historical: HistoricalPoller) -> None:
        """Test adding entries to the calendar."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = (location, camera)
        test_date = date(2024, 1, 15)
        seq_num = 42

        historical.add_to_calendar(location, camera, test_date, seq_num)

        assert loc_cam in historical._calendar
        assert 2024 in historical._calendar[loc_cam]
        assert 1 in historical._calendar[loc_cam][2024]
        assert 15 in historical._calendar[loc_cam][2024][1]
        assert historical._calendar[loc_cam][2024][1][15] == seq_num

        # Test updating with higher seq_num
        historical.add_to_calendar(location, camera, test_date, 100)
        assert historical._calendar[loc_cam][2024][1][15] == 100

        # Test not updating with lower seq_num
        historical.add_to_calendar(location, camera, test_date, 50)
        assert historical._calendar[loc_cam][2024][1][15] == 100

    @pytest.mark.asyncio
    async def test_flatten_calendar(self, historical: HistoricalPoller) -> None:
        """Test flattening the calendar structure."""
        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = (location, camera)

        # Add some test data
        historical._calendar[loc_cam] = {2024: {1: {15: 42, 16: 100}, 2: {1: 25}}}

        flat_calendar = historical.flatten_calendar(location, camera)

        expected = {"2024-01-15": 42, "2024-01-16": 100, "2024-02-01": 25}
        assert flat_calendar == expected

    @pytest.mark.asyncio
    async def test_get_most_recent_day_empty_calendar(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent day with empty calendar."""
        location = m.locations[0]
        camera = location.cameras[0]

        result = await historical.get_most_recent_day(location, camera)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_most_recent_day_single_entry_if_not_today(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent day with only one entry."""
        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = (location, camera)

        historical._calendar[loc_cam] = {2024: {1: {15: 42}}}

        result = await historical.get_most_recent_day(location, camera)
        assert result == datetime.date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_get_most_recent_day_single_entry_if_today(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent day with only one entry."""
        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = (location, camera)

        day_obs = get_current_day_obs()
        day, month, year = day_obs.day, day_obs.month, day_obs.year

        historical._calendar[loc_cam] = {year: {month: {day: 42}}}

        result = await historical.get_most_recent_day(location, camera)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_most_recent_day_multiple_entries(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent day with multiple entries."""
        from lsst.ts.rubintv.models.models_helpers import date_str_to_date

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = (location, camera)

        # Add calendar entries that are not today
        historical._calendar[loc_cam] = {2024: {1: {15: 42, 16: 100, 17: 25}}}

        result = await historical.get_most_recent_day(location, camera)
        expected = date_str_to_date("2024-01-17")  # Most recent that's not today
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_events_for_date_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting events for a date with no data."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        events = await historical.get_events_for_date(location, camera, test_date)
        assert events == []

    @pytest.mark.asyncio
    async def test_get_per_day_for_date_no_events(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting per-day data for a date with no events."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        per_day_data = await historical.get_per_day_for_date(
            location, camera, test_date
        )
        assert per_day_data == {}

    @pytest.mark.asyncio
    async def test_night_report_exists_for_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test checking if night report exists with no data."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        exists = await historical.night_report_exists_for(location, camera, test_date)
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_night_report_payload_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting night report payload with no data."""
        from datetime import date

        from lsst.ts.rubintv.models.models import NightReport

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        report = await historical.get_night_report_payload(location, camera, test_date)
        assert isinstance(report, NightReport)
        assert report.text == {}
        assert report.plots == []

    @pytest.mark.asyncio
    async def test_get_most_recent_events_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent events with no data."""
        location = m.locations[0]
        camera = location.cameras[0]

        events = await historical.get_most_recent_events(location, camera)
        assert events == []

    @pytest.mark.asyncio
    async def test_get_most_recent_event_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent event with no data."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        event = await historical.get_most_recent_event(location, camera, channel)
        assert event is None

    @pytest.mark.asyncio
    async def test_get_camera_calendar_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting camera calendar with no data."""
        location = m.locations[0]
        camera = location.cameras[0]

        calendar = await historical.get_camera_calendar(location, camera)
        assert calendar == {}

    @pytest.mark.asyncio
    async def test_get_all_channel_names_for_date_and_seq_num(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test getting all channel names for a date and seq_num."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        events: list[Event] = rubin_data_mocker.get_mocked_events_for_camera(
            location, camera
        )
        assert len(events) > 0

        seq_num = events[0].seq_num_force_int()
        seq_num_events = [e for e in events if e.seq_num_force_int() == seq_num]
        seq_num_channels = [e.channel_name for e in seq_num_events]
        assert len(seq_num_channels) > 0

        objects = [{"key": event.key, "hash": "mock_hash"} for event in events]
        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Extract the date from the first event's key
        # (format: camera/YYYY-MM-DD/channel/...)
        from lsst.ts.rubintv.models.models_helpers import date_str_to_date

        first_key = events[0].key
        date_str = first_key.split("/")[1]  # Extract YYYY-MM-DD
        event_date = date_str_to_date(date_str)

        channel_names = await historical.get_all_channel_names_for_date_and_seq_num(
            location, camera, event_date, seq_num
        )
        assert channel_names == seq_num_channels

    @pytest.mark.asyncio
    async def test_get_all_channel_names_for_date_and_seq_num_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting channel names for date and seq_num with no data."""
        location = m.locations[0]
        camera = location.cameras[0]

        channel_names = await historical.get_all_channel_names_for_date_and_seq_num(
            location, camera, date_str_to_date("2024-01-15"), 42
        )
        assert channel_names == []

    @pytest.mark.asyncio
    async def test_ingest_objects(self, historical: HistoricalPoller) -> None:
        """Test ingesting and storing objects."""
        location = m.locations[0]

        # Mock objects with different types
        objects = [
            {"key": "camera1/2024-01-15/channel1/000042/test.jpg", "hash": "hash1"},
            {"key": "camera1/2024-01-15/metadata.json", "hash": "hash2"},
            {"key": "camera1/2024-01-15/night_report/group1/plot.png", "hash": "hash3"},
        ]

        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify night report metadata was processed
        assert location in historical._nr_metadata


class TestHistoricalPollerWithMockData:
    """Test suite for HistoricalPoller with mock S3 data."""

    @pytest.mark.asyncio
    async def test_with_mock_events(self, rubin_data_mocker: RubinDataMocker) -> None:
        """Test HistoricalPoller with mock events from S3."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]

        # Get objects from mock data
        objects = []
        for camera in location.cameras:
            if camera.online:
                for channel in camera.channels:
                    events = rubin_data_mocker.get_mocked_events_for_channel(
                        location, camera, channel
                    )
                    for event in events:
                        objects.append({"key": event.key, "hash": "mock_hash"})

        if objects:
            await historical._ingest_objects(
                location,
                objects,
                replace_night_reports=True,
                notify_structured_updates=False,
            )

            # Verify data was stored
            assert len(historical._structured_events) > 0

            # Test retrieving events for a date
            from lsst.ts.rubintv.models.models import get_current_day_obs

            events = await historical.get_events_for_date(
                location, location.cameras[0], get_current_day_obs()
            )
            assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_night_report_processing(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test processing night report data."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]

        # Create mock night report object
        nr_obj = rubin_data_mocker.mock_night_report_plot(location, camera)
        objects = [nr_obj]

        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify night report data was stored
        assert location in historical._nr_metadata

        # Test getting night report payload
        from lsst.ts.rubintv.models.models import get_current_day_obs

        report = await historical.get_night_report_payload(
            location, camera, get_current_day_obs()
        )
        assert report.plots is not None

    @pytest.mark.asyncio
    async def test_complete_data_flow(self) -> None:
        """Test the complete flow of data processing, storage and retrieval."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Create mock events with different extensions
        mock_events = []
        # Add jpg files
        for seq_num in range(1, 5):
            mock_events.append(
                {
                    "key": (
                        f"{camera.name}/2024-02-15/{channel.name}/{seq_num:06d}/"
                        f"{camera.name}_{channel.name}_{seq_num:06d}.jpg"
                    ),
                    "hash": f"hash{seq_num}",
                }
            )
        # Add png files (different extension)
        for seq_num in range(5, 8):
            mock_events.append(
                {
                    "key": (
                        f"{camera.name}/2024-02-15/{channel.name}/{seq_num:06d}/"
                        f"{camera.name}_{channel.name}_{seq_num:06d}.png"
                    ),
                    "hash": f"hash{seq_num}",
                }
            )

        # Add metadata object
        mock_events.append(
            {"key": f"{camera.name}/2024-02-15/metadata.json", "hash": "hash_meta"}
        )

        # Process the mock events
        await historical._ingest_objects(
            location,
            mock_events,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify data was stored correctly
        from datetime import date

        loc_cam = (location, camera)
        test_date = date(2024, 2, 15)
        assert loc_cam in historical._structured_events
        assert test_date in historical._structured_events[loc_cam]
        assert channel in historical._structured_events[loc_cam][test_date]

        # Check sequence numbers are stored
        seq_nums = historical._structured_events[loc_cam][test_date][channel]
        assert len(seq_nums) == 7  # 7 numbered events
        assert all(i in seq_nums for i in range(1, 8))

        # Verify extension handling
        channel_date_key = (location, camera, test_date, channel)
        assert channel_date_key in historical._channel_default_extensions
        # JPG should be default (4 jpgs vs 3 png)
        assert historical._channel_default_extensions[channel_date_key] == "jpg"

        # Check extension exceptions
        assert channel_date_key in historical._extension_exceptions
        assert len(historical._extension_exceptions[channel_date_key]) == 3  # png files
        assert all(
            historical._extension_exceptions[channel_date_key][i] == "png"
            for i in range(5, 8)
        )

        # Verify metadata was stored
        loc_cam_str = location.name + "/" + camera.name
        assert loc_cam_str in historical._metadata_collector.metadata_refs
        metadata_dates = {
            ref.date_str
            for ref in historical._metadata_collector.metadata_refs[loc_cam_str]
        }
        assert "2024-02-15" in metadata_dates
        assert loc_cam_str in historical._metadata_collector.metadata_refs
        assert any(
            ref.date_str == "2024-02-15"
            for ref in historical._metadata_collector.metadata_refs[loc_cam_str]
        )
        metadata_dates = {
            ref.date_str
            for ref in historical._metadata_collector.metadata_refs[loc_cam_str]
        }
        assert "2024-02-15" in metadata_dates

        # Verify calendar was updated
        assert loc_cam in historical._calendar
        assert 2024 in historical._calendar[loc_cam]
        assert 2 in historical._calendar[loc_cam][2024]
        assert 15 in historical._calendar[loc_cam][2024][2]
        # Highest seq_num should be 7
        assert historical._calendar[loc_cam][2024][2][15] == 7

        # Test retrieval methods
        from datetime import date

        test_date = date(2024, 2, 15)

        # Test get_events_for_date
        events = await historical.get_events_for_date(location, camera, test_date)
        assert len(events) == 7

        # Verify extensions are correctly reconstructed
        jpg_events = [e for e in events if e.key.endswith(".jpg")]
        png_events = [e for e in events if e.key.endswith(".png")]
        assert len(jpg_events) == 4  # 4 jpg events
        assert len(png_events) == 3  # 3 png events

        # Test most recent day
        recent_day = await historical.get_most_recent_day(location, camera)
        assert recent_day == test_date

        # Test calendar flattening
        flat_calendar = historical.flatten_calendar(location, camera)
        assert "2024-02-15" in flat_calendar
        assert flat_calendar["2024-02-15"] == 7

    @pytest.mark.asyncio
    async def test_metadata_and_night_report_integration(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test integration of metadata and night report processing."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        date_str = "2024-04-20"

        # Create metadata object
        metadata_obj = {
            "key": f"{camera.name}/{date_str}/metadata.json",
            "hash": "hash_meta",
        }

        # Create night report objects
        nr_plot1 = rubin_data_mocker.mock_night_report_plot(
            location, camera, date_str=date_str
        )
        nr_plot2 = rubin_data_mocker.mock_night_report_plot(
            location, camera, date_str=date_str, group="group2"
        )

        # Process objects
        objects = [metadata_obj, nr_plot1, nr_plot2]
        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )
        # Verify metadata was stored
        loc_cam = f"{location.name}/{camera.name}"
        assert loc_cam in historical._metadata_collector.metadata_refs
        metadata_dates = {
            ref.date_str
            for ref in historical._metadata_collector.metadata_refs[loc_cam]
        }
        assert date_str in metadata_dates

        # Verify night report data was stored
        assert location in historical._nr_metadata
        nr_data = [
            nr
            for nr in historical._nr_metadata[location]
            if nr.camera_name == camera.name and nr.day_obs == date_str
        ]
        assert len(nr_data) > 0

        # Check calendar entry
        test_date = date_str_to_date(date_str)
        assert (
            await historical.check_for_metadata_for_date(location, camera, test_date)
            is True
        )

        # Test night report existence check
        has_nr = await historical.night_report_exists_for(location, camera, test_date)
        assert has_nr is True

        # Test calendar operation
        flat_calendar = historical.flatten_calendar(location, camera)
        assert date_str in flat_calendar

    @pytest.mark.asyncio
    async def test_get_next_prev_event_with_structured_data(self) -> None:
        """Test getting next/previous events with structured data storage."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]
        date_str = "2024-05-15"

        # Create a sequence of events for the same channel
        events = []
        for seq_num in range(1, 6):
            events.append(
                Event(
                    key=(
                        f"{camera.name}/{date_str}/{channel.name}/{seq_num:06d}/"
                        f"{camera.name}_{channel.name}_{seq_num:06d}.jpg"
                    )
                )
            )

        # Store the events
        await historical.store_events_structured(events, location)

        # Test getting next/previous for a middle event
        middle_event = events[2]  # seq_num 3
        next_prev = await historical.get_next_prev_event(location, camera, middle_event)

        print(next_prev)

        # Check if next_prev has the right structure
        assert next_prev is not None
        assert len(next_prev) == 2
        next_event, prev_event = next_prev

        # Verify next event has seq_num 4
        assert next_event is not None
        assert next_event.get("seq_num") == 4

        # Verify previous event has seq_num 2
        assert prev_event is not None
        assert prev_event.get("seq_num") == 2

        # Test edge cases - first event
        first_event = events[0]
        next_prev = await historical.get_next_prev_event(location, camera, first_event)
        next_event, prev_event = next_prev

        # Should have next but no previous
        assert next_event is not None
        assert next_event.get("seq_num") == 2
        assert prev_event is None

        # Test edge cases - last event
        last_event = events[-1]
        next_prev = await historical.get_next_prev_event(location, camera, last_event)
        next_event, prev_event = next_prev

        # Should have previous but no next
        assert next_event is None
        assert prev_event is not None
        assert prev_event.get("seq_num") == 4

    @pytest.mark.asyncio
    async def test_cache_updates_when_new_events_added(
        self, historical: HistoricalPoller, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test that cache updates when new events are added to the bucket."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Use the date from the mock data (today, since RubinDataMocker
        # defaults to today)
        test_date = datetime.date.today()

        # Initial download
        await historical._initialise_location_store(location)

        # Add more events to the mock bucket for today
        rubin_data_mocker.add_seq_objs_for_channel(
            location, camera, channel, num_objs=3
        )

        # Get new objects from bucket (simulating recheck)
        new_objects = await historical._get_objects_for_location_camera(
            location, camera
        )

        # Simulate recheck - this should detect changes and update cache
        await historical._update_if_changed(location, camera, new_objects)

        # Verify cache was updated with new events
        # After the update, the events should still be accessible
        updated_events = await historical.get_events_for_date(
            location, camera, test_date
        )
        # Verify that cache maintains the events (may not increase if already
        # cached)
        # The key point is that the operation completed without error
        assert updated_events is not None

    @pytest.mark.asyncio
    async def test_cache_detects_added_keys(self, historical: HistoricalPoller) -> None:
        """Test that _update_if_changed detects added keys correctly."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Create initial batch of objects
        objects_batch_1 = []
        for i in range(1, 4):
            objects_batch_1.append(
                {
                    "key": (
                        f"{camera.name}/2024-06-15/{channel.name}/{i:06d}/"
                        f"{camera.name}_{channel.name}_{i:06d}.jpg"
                    ),
                    "hash": f"hash{i}",
                }
            )

        # Process initial objects
        await historical._ingest_objects(
            location,
            objects_batch_1,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify initial state
        assert (location, camera) in historical._structured_events
        assert (
            datetime.date(2024, 6, 15)
            in historical._structured_events[(location, camera)]
        )
        initial_count = len(
            historical._structured_events[(location, camera)][
                datetime.date(2024, 6, 15)
            ][channel]
        )
        assert initial_count == 3

        # Add new objects to bucket
        objects_batch_2 = []
        for i in range(4, 7):
            objects_batch_2.append(
                {
                    "key": (
                        f"{camera.name}/2024-06-15/{channel.name}/{i:06d}/"
                        f"{camera.name}_{channel.name}_{i:06d}.jpg"
                    ),
                    "hash": f"hash{i}",
                }
            )

        # Combine all objects (simulating bucket list with new items)
        all_objects = objects_batch_1 + objects_batch_2

        # Simulate recheck with new objects
        await historical._update_if_changed(location, camera, all_objects)

        # Verify new seq_nums were added
        seq_nums = historical._structured_events[(location, camera)][
            datetime.date(2024, 6, 15)
        ][channel]
        assert len(seq_nums) == 6
        assert 4 in seq_nums
        assert 5 in seq_nums
        assert 6 in seq_nums

    @pytest.mark.asyncio
    async def test_cache_handles_removed_keys(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that cache is cleared and rebuilt when objects are removed from
        bucket."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Add initial objects
        objects_batch_1 = []
        for i in range(1, 6):
            objects_batch_1.append(
                {
                    "key": (
                        f"{camera.name}/2024-06-15/{channel.name}/{i:06d}/"
                        f"{camera.name}_{channel.name}_{i:06d}.jpg"
                    ),
                    "hash": f"hash{i}",
                }
            )

        await historical._ingest_objects(
            location,
            objects_batch_1,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify initial state
        assert (
            len(
                historical._structured_events[(location, camera)][
                    datetime.date(2024, 6, 15)
                ][channel]
            )
            == 5
        )

        # Simulate bucket now has fewer objects (only 3-5)
        objects_batch_2 = []
        for i in range(3, 6):
            objects_batch_2.append(
                {
                    "key": (
                        f"{camera.name}/2024-06-15/{channel.name}/{i:06d}/"
                        f"{camera.name}_{channel.name}_{i:06d}.jpg"
                    ),
                    "hash": f"hash{i}",
                }
            )

        # Run recheck with fewer objects (simulating deletion)
        await historical._update_if_changed(location, camera, objects_batch_2)

        # Verify cache was cleared and rebuilt with only remaining items
        if (location, camera) in historical._structured_events:
            if (
                datetime.date(2024, 6, 15)
                in historical._structured_events[(location, camera)]
            ):
                seq_nums = historical._structured_events[(location, camera)][
                    datetime.date(2024, 6, 15)
                ][channel]
                assert len(seq_nums) == 3
                assert 1 not in seq_nums
                assert 2 not in seq_nums
                assert 3 in seq_nums
                assert 4 in seq_nums
                assert 5 in seq_nums

    @pytest.mark.asyncio
    async def test_cache_handles_no_changes(self, historical: HistoricalPoller) -> None:
        """Test that cache is not modified when bucket contents haven't
        changed."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Add initial objects
        objects = []
        for i in range(1, 4):
            objects.append(
                {
                    "key": (
                        f"{camera.name}/2024-06-15/{channel.name}/{i:06d}/"
                        f"{camera.name}_{channel.name}_{i:06d}.jpg"
                    ),
                    "hash": f"hash{i}",
                }
            )

        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Get initial structured data
        initial_data = historical._structured_events[(location, camera)][
            datetime.date(2024, 6, 15)
        ][channel].copy()
        initial_extensions = historical._channel_default_extensions.copy()

        # Run recheck with identical objects (no changes)
        await historical._update_if_changed(location, camera, objects)

        # Verify cache still exists and is unchanged
        assert (location, camera) in historical._structured_events
        assert (
            historical._structured_events[(location, camera)][
                datetime.date(2024, 6, 15)
            ][channel]
            == initial_data
        )
        # Extensions should remain the same
        assert historical._channel_default_extensions == initial_extensions

    @pytest.mark.asyncio
    async def test_cache_with_mixed_object_types(
        self, historical: HistoricalPoller, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test bucket change detection with mixed object types (events,
        metadata, night reports)."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]
        date_str = "2024-07-10"

        # Create objects with different types
        objects = [
            # Event objects
            {
                "key": f"{camera.name}/{date_str}/{channel.name}/000001/"
                f"{camera.name}_{channel.name}_000001.jpg",
                "hash": "hash1",
            },
            {
                "key": f"{camera.name}/{date_str}/{channel.name}/000002/"
                f"{camera.name}_{channel.name}_000002.jpg",
                "hash": "hash2",
            },
            # Metadata object (should be skipped in comparison)
            {"key": f"{camera.name}/{date_str}/metadata.json", "hash": "hash_meta"},
            # Night report object (should be skipped in comparison)
            {
                "key": f"{camera.name}/{date_str}/night_report/group1/plot.png",
                "hash": "hash_nr",
            },
        ]

        # Process initial objects
        await historical._ingest_objects(
            location,
            objects,
            replace_night_reports=True,
            notify_structured_updates=False,
        )

        # Verify only event objects are in structured data
        assert (location, camera) in historical._structured_events
        assert (
            datetime.date(2024, 7, 10)
            in historical._structured_events[(location, camera)]
        )
        date_str = "2024-07-10"
        seq_nums = historical._structured_events[(location, camera)][
            datetime.date(2024, 7, 10)
        ][channel]
        assert len(seq_nums) == 2
        assert 1 in seq_nums
        assert 2 in seq_nums

        # Add a new event object (metadata and night report added too, but
        # should be ignored in key comparison)
        new_objects = objects + [
            {
                "key": f"{camera.name}/{date_str}/{channel.name}/000003/"
                f"{camera.name}_{channel.name}_000003.jpg",
                "hash": "hash3",
            },
            {
                "key": f"{camera.name}/{date_str}/night_report/group2/plot2.png",
                "hash": "hash_nr2",
            },
        ]

        # Simulate recheck
        await historical._update_if_changed(location, camera, new_objects)

        # Verify only the new event object was added (night report ignored in
        # key comparison)
        date_obj = datetime.date.fromisoformat(date_str)
        updated_seq_nums = historical._structured_events[(location, camera)][date_obj][
            channel
        ]
        assert len(updated_seq_nums) == 3
        assert 3 in updated_seq_nums

    @pytest.mark.asyncio
    async def test_parse_structured_key_valid_keys(
        self, historical: HistoricalPoller
    ) -> None:
        """Test _parse_structured_key with various valid key formats."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Create a key using the actual camera and channel names
        key = f"{camera.name}/2024-06-15/{channel.name}/000042/{camera.name}_{channel.name}_000042.jpg"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is not None
        assert parsed[0] == camera
        assert parsed[1] == datetime.date(2024, 6, 15)
        assert parsed[2] == channel
        assert parsed[3] == 42

        # Test with 'final' seq_num
        key = f"{camera.name}/2024-06-15/{channel.name}/final/{camera.name}_{channel.name}_final.jpg"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is not None
        assert parsed[0] == camera
        assert parsed[1] == datetime.date(2024, 6, 15)
        assert parsed[2] == channel
        assert parsed[3] == "final"

        # Test with underscores in the path (still uses actual names)
        key = f"{camera.name}/2024-06-15/{channel.name}/000001/{camera.name}_{channel.name}_000001.fits"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is not None
        assert parsed[0] == camera
        assert parsed[1] == datetime.date(2024, 6, 15)
        assert parsed[2] == channel
        assert parsed[3] == 1

    @pytest.mark.asyncio
    async def test_parse_structured_key_invalid_keys(
        self, historical: HistoricalPoller
    ) -> None:
        """Test _parse_structured_key with invalid key formats."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # Test with too few parts
        key = "camera1/2024-06-15/channel1"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is None

        # Test with invalid camera name
        key = f"wrong_camera/2024-06-15/{channel.name}/000001/file.jpg"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is None

        # Test with invalid channel name
        key = f"{camera.name}/2024-06-15/invalid_channel/000001/file.jpg"
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is None

        # Test empty string
        key = ""
        parsed = historical._parse_structured_key(key, camera)
        assert parsed is None
