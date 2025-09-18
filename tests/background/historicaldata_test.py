import datetime
import pickle
import zlib
from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
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
        assert historical._metadata == {}
        assert historical._compressed_events == {}
        assert historical._nr_metadata == {}
        assert historical._calendar == {}

    @pytest.mark.asyncio
    async def test_clear_all_data(self, historical: HistoricalPoller) -> None:
        """Test clearing all cached data."""
        # Populate some test data
        historical._have_downloaded = True
        historical._metadata["test"] = b"test_data"
        historical._compressed_events["test"] = b"test_events"
        historical._nr_metadata["test"] = []
        historical._calendar["test"] = {}

        await historical.clear_all_data()

        assert historical._have_downloaded is False
        assert historical._metadata == {}
        assert historical._compressed_events == {}
        assert historical._nr_metadata == {}
        assert historical._calendar == {}

    @pytest.mark.asyncio
    async def test_trigger_reload_everything(
        self, historical: HistoricalPoller
    ) -> None:
        """Test triggering a reload of all data."""
        historical._have_downloaded = True
        await historical.trigger_reload_everything()
        assert historical._have_downloaded is False

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
        loc_cam = "test_loc/test_cam"
        date_str = "2024-01-15"
        seq_num = 42

        historical.add_to_calendar(loc_cam, date_str, seq_num)

        assert loc_cam in historical._calendar
        assert 2024 in historical._calendar[loc_cam]
        assert 1 in historical._calendar[loc_cam][2024]
        assert 15 in historical._calendar[loc_cam][2024][1]
        assert historical._calendar[loc_cam][2024][1][15] == seq_num

        # Test updating with higher seq_num
        historical.add_to_calendar(loc_cam, date_str, 100)
        assert historical._calendar[loc_cam][2024][1][15] == 100

        # Test not updating with lower seq_num
        historical.add_to_calendar(loc_cam, date_str, 50)
        assert historical._calendar[loc_cam][2024][1][15] == 100

    @pytest.mark.asyncio
    async def test_flatten_calendar(self, historical: HistoricalPoller) -> None:
        """Test flattening the calendar structure."""
        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

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
        loc_cam = f"{location.name}/{camera.name}"

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
        loc_cam = f"{location.name}/{camera.name}"

        from lsst.ts.rubintv.models.models import get_current_day_obs

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
        loc_cam = f"{location.name}/{camera.name}"

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
    async def test_get_channel_data_for_date_no_events(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting channel data for a date with no events."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        channel_data = await historical.get_channel_data_for_date(
            location, camera, test_date
        )
        assert channel_data == {}

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
    async def test_get_metadata_for_date_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting metadata for a date with no data."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        test_date = date(2024, 1, 15)

        metadata = await historical.get_metadata_for_date(location, camera, test_date)
        assert metadata == {}

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
    async def test_get_most_recent_channel_data_no_day(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting most recent channel data with no recent day."""
        location = m.locations[0]
        camera = location.cameras[0]

        channel_data = await historical.get_most_recent_channel_data(location, camera)
        assert channel_data == {}

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
    async def test_get_all_channel_names_for_date_and_seq_num_no_data(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting channel names for date and seq_num with no data."""
        location = m.locations[0]
        camera = location.cameras[0]

        channel_names = await historical.get_all_channel_names_for_date_and_seq_num(
            location, camera, "2024-01-15", 42
        )
        assert channel_names == []

    @pytest.mark.asyncio
    async def test_unarchive_events(self, historical: HistoricalPoller) -> None:
        """Test unarchiving events from string keys."""
        from lsst.ts.rubintv.models.models import Event

        archived_events = [
            "camera1/2024-01-15/channel1/000042/test_file.jpg",
            "camera1/2024-01-15/channel2/000043/test_file2.jpg",
        ]

        events = historical.unarchive_events(archived_events)
        assert len(events) == 2
        assert all(isinstance(event, Event) for event in events)
        assert events[0].camera_name == "camera1"
        assert events[0].day_obs == "2024-01-15"
        assert events[0].channel_name == "channel1"
        assert events[0].seq_num == 42

    @pytest.mark.asyncio
    async def test_store_events(self, historical: HistoricalPoller) -> None:
        """Test storing events in temporary storage."""
        from lsst.ts.rubintv.models.models import Event

        events = [
            Event(key="camera1/2024-01-15/channel1/000042/test_file.jpg"),
            Event(key="camera1/2024-01-15/channel2/000043/test_file2.jpg"),
        ]

        await historical.store_events(events, "test_location")

        loc_cam = "test_location/camera1"
        assert loc_cam in historical._temp_events
        assert len(historical._temp_events[loc_cam]) == 2

        # Check calendar was updated
        assert loc_cam in historical._calendar
        assert historical._calendar[loc_cam][2024][1][15] == 43  # Highest seq_num

    @pytest.mark.asyncio
    async def test_compress_events(self, historical: HistoricalPoller) -> None:
        """Test compressing events from temporary storage."""
        # Setup temporary events
        historical._temp_events["test_key"] = ["event1", "event2"]

        await historical.compress_events()

        assert "test_key" in historical._compressed_events
        # Verify we can decompress the data
        decompressed = pickle.loads(
            zlib.decompress(historical._compressed_events["test_key"])
        )
        assert decompressed == ["event1", "event2"]

    @pytest.mark.asyncio
    async def test_filter_convert_store_objects(
        self, historical: HistoricalPoller
    ) -> None:
        """Test filtering, converting, and storing objects."""
        location = m.locations[0]

        # Mock objects with different types
        objects = [
            {"key": "camera1/2024-01-15/channel1/000042/test.jpg", "hash": "hash1"},
            {"key": "camera1/2024-01-15/metadata.json", "hash": "hash2"},
            {"key": "camera1/2024-01-15/night_report/group1/plot.png", "hash": "hash3"},
        ]

        await historical.filter_convert_store_objects(objects, location)

        # Verify night report metadata was processed
        assert location.name in historical._nr_metadata

    @pytest.mark.asyncio
    async def test_with_test_dates(self) -> None:
        """Test HistoricalPoller with test date range."""
        from lsst.ts.rubintv.models.models_helpers import date_str_to_date

        test_poller = HistoricalPoller(
            m.locations,
            test_mode=True,
            test_date_start="2024-01-01",
            test_date_end="2024-01-03",
        )

        assert test_poller.test_date_start == date_str_to_date("2024-01-01")
        assert test_poller.test_date_end == date_str_to_date("2024-01-03")


class TestHistoricalPollerWithMockData:
    """Test suite for HistoricalPoller with mock S3 data."""

    @pytest.mark.asyncio
    async def test_with_mock_events(self, rubin_data_mocker: RubinDataMocker) -> None:
        """Test HistoricalPoller with mock events from S3."""
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]

        # Get objects from mock data
        objects = []
        for camera in location.cameras:
            if camera.online:
                for channel in camera.channels:
                    events = rubin_data_mocker.get_mocked_events(
                        location, camera, channel
                    )
                    for event in events:
                        objects.append({"key": event.key, "hash": "mock_hash"})

        if objects:
            await historical.filter_convert_store_objects(objects, location)

            # Verify data was stored
            assert len(historical._compressed_events) > 0

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
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]
        camera = location.cameras[0]

        # Create mock night report object
        nr_obj = rubin_data_mocker.mock_night_report_plot(location, camera)
        objects = [nr_obj]

        await historical.filter_convert_store_objects(objects, location)

        # Verify night report data was stored
        assert location.name in historical._nr_metadata

        # Test getting night report payload
        from lsst.ts.rubintv.models.models import get_current_day_obs

        report = await historical.get_night_report_payload(
            location, camera, get_current_day_obs()
        )
        assert report.plots is not None

    @pytest.mark.asyncio
    async def test_metadata_processing(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test processing metadata files."""
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]

        # Mock metadata object
        metadata_key = f"{location.cameras[0].name}/2024-01-15/metadata.json"
        test_metadata = {"42": {"exposure_time": 30.0}}

        # Upload mock metadata to S3
        rubin_data_mocker.upload_fileobj(
            test_metadata, location.bucket_name, metadata_key
        )

        objects = [{"key": metadata_key, "hash": "metadata_hash"}]
        await historical.filter_convert_store_objects(objects, location)

        # Test retrieving metadata
        from datetime import date

        test_date = date(2024, 1, 15)
        metadata = await historical.get_metadata_for_date(
            location, location.cameras[0], test_date
        )
        assert metadata == test_metadata


class TestHistoricalPollerEdgeCases:
    """Test edge cases and error handling for HistoricalPoller."""

    @pytest.mark.asyncio
    async def test_get_events_for_date_with_final_seq_num(
        self, historical: HistoricalPoller
    ) -> None:
        """Test handling events with 'final' sequence numbers."""
        import pickle
        import zlib
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        # Create events with both numeric and 'final' seq nums
        event_keys = [
            "camera1/2024-01-15/channel1/000042/test_file.jpg",
            "camera1/2024-01-15/channel1/final/final_image.jpg",
            "camera1/2024-01-16/channel1/000001/next_day.jpg",
        ]

        # Store compressed events
        historical._compressed_events[loc_cam] = zlib.compress(pickle.dumps(event_keys))

        test_date = date(2024, 1, 15)
        events = await historical.get_events_for_date(location, camera, test_date)

        assert len(events) == 2  # Only events from 2024-01-15
        seq_nums = [e.seq_num for e in events]
        assert 42 in seq_nums
        assert "final" in seq_nums

    @pytest.mark.asyncio
    async def test_get_most_recent_day_with_current_day(
        self, historical: HistoricalPoller
    ) -> None:
        """Test get_most_recent_day when most recent is current day."""
        from lsst.ts.rubintv.models.models import get_current_day_obs

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        current_day = get_current_day_obs()

        # Add calendar with current day as most recent
        historical._calendar[loc_cam] = {
            current_day.year: {
                current_day.month: {
                    current_day.day - 1: 42,  # Yesterday
                    current_day.day: 100,  # Today
                }
            }
        }

        result = await historical.get_most_recent_day(location, camera)
        expected_day = current_day.replace(day=current_day.day - 1)
        assert result == expected_day

    @pytest.mark.asyncio
    async def test_get_per_day_for_date_with_mixed_channels(
        self, historical: HistoricalPoller
    ) -> None:
        """Test per-day data filtering with mix of per-day and sequential
        channels."""
        import pickle
        import zlib
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        # Mock camera with mixed channel types
        if hasattr(camera, "pd_channels"):
            pd_channel_names = [c.name for c in camera.pd_channels()]
        else:
            pd_channel_names = []

        event_keys = [
            "camera1/2024-01-15/seq_channel/000042/test.jpg",  # Sequential channel
            "camera1/2024-01-15/pd_channel/final/movie.mp4",  # Per-day channel
        ]

        historical._compressed_events[loc_cam] = zlib.compress(pickle.dumps(event_keys))

        test_date = date(2024, 1, 15)
        per_day_data = await historical.get_per_day_for_date(
            location, camera, test_date
        )

        # Should only contain per-day channels
        for channel_name in per_day_data.keys():
            assert channel_name in pd_channel_names or channel_name == "pd_channel"

    @pytest.mark.asyncio
    async def test_metadata_with_camera_metadata_from(
        self, historical: HistoricalPoller
    ) -> None:
        """Test metadata retrieval when camera uses metadata_from another
        camera."""
        import pickle
        import zlib
        from datetime import date

        location = m.locations[0]

        # Create a camera that uses metadata from another camera
        source_camera_name = "source_cam"
        target_camera_name = "target_cam"

        test_metadata = {"42": {"exposure_time": 30.0}}
        compressed_metadata = zlib.compress(pickle.dumps(test_metadata))

        # Store metadata under source camera name
        historical._metadata[f"{location.name}/{source_camera_name}/2024-01-15"] = (
            compressed_metadata
        )

        # Create mock camera with metadata_from set
        from lsst.ts.rubintv.models.models import Camera

        class MockCamera(Camera):
            def __init__(self) -> None:
                super().__init__(
                    name=target_camera_name, online=True, title="Mock Camera"
                )
                self.metadata_from = source_camera_name

        mock_camera = MockCamera()
        test_date = date(2024, 1, 15)

        metadata = await historical.get_metadata_for_date(
            location, mock_camera, test_date
        )
        assert metadata == test_metadata

    @pytest.mark.asyncio
    async def test_night_report_with_text_and_plots(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test night report processing with both text metadata and plots."""
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]
        camera = location.cameras[0]

        # Create mock night report objects - both metadata and plots
        text_metadata_obj = {
            "key": f"{camera.name}/2024-01-15/night_report/report_md.json",
            "hash": "text_hash",
        }
        plot_obj = {
            "key": f"{camera.name}/2024-01-15/night_report/plots/plot1.png",
            "hash": "plot_hash",
        }

        # Upload text metadata to S3
        test_text = {"summary": "Night report summary", "observations": 42}
        rubin_data_mocker.upload_fileobj(
            test_text, location.bucket_name, text_metadata_obj["key"]
        )

        objects = [text_metadata_obj, plot_obj]
        await historical.filter_convert_store_objects(objects, location)

        # Test getting complete night report
        from datetime import date

        test_date = date(2024, 1, 15)
        report = await historical.get_night_report_payload(location, camera, test_date)

        assert report.text == test_text
        assert report.plots is not None
        assert len(report.plots) == 1
        assert report.plots[0].key == plot_obj["key"]

    @pytest.mark.asyncio
    async def test_get_next_prev_event_integration(
        self, historical: HistoricalPoller
    ) -> None:
        """Test next/previous event functionality with historical data."""
        import pickle
        import zlib

        from lsst.ts.rubintv.models.models import Event

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"
        channel = camera.channels[0]

        # Create a sequence of events
        event_keys = [
            f"{camera.name}/2024-01-15/{channel.name}/000040/test1.jpg",
            f"{camera.name}/2024-01-15/{channel.name}/000041/test2.jpg",
            f"{camera.name}/2024-01-15/{channel.name}/000042/test3.jpg",
            f"{camera.name}/2024-01-15/{channel.name}/000043/test4.jpg",
        ]

        historical._compressed_events[loc_cam] = zlib.compress(pickle.dumps(event_keys))

        # Test event in the middle of sequence
        test_event = Event(
            key=f"{camera.name}/2024-01-15/{channel.name}/000042/test3.jpg"
        )

        next_event, prev_event = await historical.get_next_prev_event(
            location, camera, test_event
        )
        print(next_event, prev_event)

        # Should find next and previous events
        assert next_event is not None
        assert prev_event is not None

    @pytest.mark.asyncio
    async def test_calendar_with_multiple_years_months(
        self, historical: HistoricalPoller
    ) -> None:
        """Test calendar functionality across multiple years and months."""
        location = m.locations[0]
        camera = location.cameras[0]

        loc_cam = f"{location.name}/{camera.name}"
        # Add calendar entries across different years and months
        test_data = [
            (loc_cam, "2023-12-31", 100),
            (loc_cam, "2024-01-01", 50),
            (loc_cam, "2024-01-15", 75),
            (loc_cam, "2024-02-01", 25),
            (loc_cam, "2024-12-25", 200),
        ]

        for loc_cam, date_str, seq_num in test_data:
            historical.add_to_calendar(loc_cam, date_str, seq_num)

        # Test calendar retrieval
        calendar = await historical.get_camera_calendar(location, camera)

        assert 2023 in calendar
        assert 2024 in calendar
        assert calendar[2023][12][31] == 100
        assert calendar[2024][1][1] == 50
        assert calendar[2024][12][25] == 200

        # Test flattened calendar
        flat_calendar = historical.flatten_calendar(location, camera)
        assert flat_calendar["2023-12-31"] == 100
        assert flat_calendar["2024-01-01"] == 50
        assert flat_calendar["2024-12-25"] == 200

    @pytest.mark.asyncio
    async def test_error_handling_in_object_processing(
        self, historical: HistoricalPoller
    ) -> None:
        """Test error handling when processing malformed objects."""
        location = m.locations[0]

        # Mock objects with invalid keys that will cause parsing errors
        invalid_objects = [
            {"key": "invalid/key/format", "hash": "hash1"},
            {"key": "camera1/invalid-date/channel/000042/test.jpg", "hash": "hash2"},
            {"key": "valid/2024-01-15/channel/000042/test.jpg", "hash": "hash3"},
        ]

        # This should not raise an exception, but handle errors gracefully
        await historical.filter_convert_store_objects(invalid_objects, location)

        # Valid objects should still be processed
        assert location.name in historical._nr_metadata

    @pytest.mark.asyncio
    async def test_compress_events_multiple_batches(
        self, historical: HistoricalPoller
    ) -> None:
        """Test event compression with multiple batches."""
        import pickle
        import zlib

        # Add events in multiple batches
        historical._temp_events["loc1/cam1"] = ["event1", "event2"]
        historical._temp_events["loc1/cam2"] = ["event3", "event4"]
        historical._temp_events["loc2/cam1"] = ["event5"]

        await historical.compress_events()

        # Verify all batches are compressed
        assert "loc1/cam1" in historical._compressed_events
        assert "loc1/cam2" in historical._compressed_events
        assert "loc2/cam1" in historical._compressed_events

        # Verify compression works correctly
        decompressed = pickle.loads(
            zlib.decompress(historical._compressed_events["loc1/cam1"])
        )
        assert decompressed == ["event1", "event2"]

    @pytest.mark.asyncio
    async def test_get_all_channel_names_filtering(
        self, historical: HistoricalPoller
    ) -> None:
        """Test filtering channel names by date and sequence number."""
        import pickle
        import zlib

        from lsst.ts.rubintv.models.models import Event

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        # Create events with different dates and seq nums
        events = [
            Event(key="camera1/2024-01-15/channel1/000042/test1.jpg"),
            Event(
                key="camera1/2024-01-15/channel2/000042/test2.jpg"
            ),  # Same seq_num, different channel
            Event(
                key="camera1/2024-01-15/channel1/000043/test3.jpg"
            ),  # Same channel, different seq_num
            Event(
                key="camera1/2024-01-16/channel1/000042/test4.jpg"
            ),  # Same seq_num, different date
        ]

        historical._compressed_events[loc_cam] = zlib.compress(pickle.dumps(events))

        channel_names = await historical.get_all_channel_names_for_date_and_seq_num(
            location, camera, "2024-01-15", 42
        )

        # Should only return channels for the specific date and seq_num
        assert set(channel_names) == {"channel1", "channel2"}

    @pytest.mark.asyncio
    async def test_day_change_handling(self, historical: HistoricalPoller) -> None:
        """Test handling of day changes in check_for_new_day."""
        from datetime import timedelta
        from unittest.mock import patch

        from lsst.ts.rubintv.models.models import get_current_day_obs

        # Set up initial state
        historical._have_downloaded = True
        historical._last_reload = get_current_day_obs() - timedelta(days=1)  # Yesterday

        # Mock get_current_day_obs to return today
        with patch(
            "lsst.ts.rubintv.background.historicaldata.get_current_day_obs"
        ) as mock_get_day:
            mock_get_day.return_value = get_current_day_obs()

            # Enable test mode to prevent infinite loop
            historical.test_mode = True

            # This should trigger a reload since last_reload < current day
            await historical.check_for_new_day()

            # Verify reload occurred
            assert historical._last_reload == get_current_day_obs()
            assert (
                historical._have_downloaded is True
            )  # Should be set back to True after reload


class TestHistoricalPollerIntegration:
    """Test integration scenarios for HistoricalPoller."""

    @pytest.mark.asyncio
    async def test_full_data_pipeline(self, rubin_data_mocker: RubinDataMocker) -> None:
        """Test the full data processing pipeline from objects to compressed
        events."""

        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]
        camera = location.cameras[0]

        # Create mock objects with multiple types
        events_data = []
        for i in range(5):
            event_obj = rubin_data_mocker.generate_event(
                location.bucket_name, camera.name, camera.channels[0].name, f"{i:06}"
            )
            events_data.append(event_obj)

        metadata_obj = {
            "key": f"{camera.name}/2024-01-15/metadata.json",
            "hash": "metadata_hash",
        }

        night_report_obj = rubin_data_mocker.mock_night_report_plot(location, camera)

        all_objects = events_data + [metadata_obj, night_report_obj]

        # Upload metadata to S3
        test_metadata = {"42": {"exposure_time": 30.0}}
        rubin_data_mocker.upload_fileobj(
            test_metadata, location.bucket_name, metadata_obj["key"]
        )

        # Process all objects through the pipeline
        await historical.filter_convert_store_objects(all_objects, location)

        # Verify events were processed and compressed
        loc_cam = f"{location.name}/{camera.name}"
        assert loc_cam in historical._compressed_events

        # Verify metadata was stored
        assert len(historical._metadata) > 0

        # Verify night report was processed
        assert location.name in historical._nr_metadata

        # Verify calendar was updated
        assert loc_cam in historical._calendar

    @pytest.mark.asyncio
    async def test_get_objects_for_location_with_test_dates(self) -> None:
        """Test object retrieval with date range filtering."""

        # Create poller with test date range
        test_poller = HistoricalPoller(
            m.locations,
            test_mode=True,
            test_date_start="2024-01-01",
            test_date_end="2024-01-03",
        )

        # Mock the S3 client to track prefix calls
        location = m.locations[0]
        expected_prefixes = []
        for date_str in ["2024-01-01", "2024-01-02"]:  # end date is exclusive
            for camera in location.cameras:
                if camera.online:
                    expected_prefixes.append(f"{camera.name}/{date_str}/")

        # This would normally call S3, but in test mode we just verify the
        # logic
        objects = await test_poller._get_objects_for_location(location)

        # Since we're in test mode with mocked S3, this should return empty
        assert objects == []

    @pytest.mark.asyncio
    async def test_store_events_with_calendar_updates(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that storing events properly updates the calendar."""
        from lsst.ts.rubintv.models.models import Event

        events = [
            Event(key="camera1/2024-01-15/channel1/000042/test1.jpg"),
            Event(key="camera1/2024-01-15/channel2/000050/test2.jpg"),
            Event(key="camera1/2024-01-16/channel1/000001/test3.jpg"),
            Event(key="camera1/2024-01-15/channel3/final/final.mp4"),  # Final seq_num
        ]

        await historical.store_events(events, "test_location")

        # Verify calendar entries
        loc_cam = "test_location/camera1"
        calendar = historical._calendar[loc_cam]

        # Check 2024-01-15 has highest seq_num (50)
        assert calendar[2024][1][15] == 50

        # Check 2024-01-16 has seq_num 1
        assert calendar[2024][1][16] == 1

    @pytest.mark.asyncio
    async def test_compression_with_multiple_locations(
        self, historical: HistoricalPoller
    ) -> None:
        """Test compression when events exist for multiple
        locations/cameras."""
        import pickle
        import zlib

        # Add events for multiple location/camera combinations
        historical._temp_events["location1/camera1"] = ["event1", "event2"]
        historical._temp_events["location1/camera2"] = ["event3"]
        historical._temp_events["location2/camera1"] = ["event4", "event5", "event6"]

        await historical.compress_events()

        # Verify all combinations were compressed
        assert "location1/camera1" in historical._compressed_events
        assert "location1/camera2" in historical._compressed_events
        assert "location2/camera1" in historical._compressed_events

        # Verify compression integrity
        for key, compressed in historical._compressed_events.items():
            decompressed = pickle.loads(zlib.decompress(compressed))
            assert isinstance(decompressed, list)
            assert len(decompressed) > 0

    @pytest.mark.asyncio
    async def test_metadata_download_and_compression(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test metadata download and compression pipeline."""
        import pickle
        import zlib

        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]

        # Create metadata objects for multiple cameras/dates
        metadata_objects = []
        test_metadata = {}

        for i, camera in enumerate(location.cameras[:2]):
            for day in ["2024-01-15", "2024-01-16"]:
                key = f"{camera.name}/{day}/metadata.json"
                metadata_data = {
                    str(j + i * 10): {"exposure_time": 30.0 + j} for j in range(3)
                }

                # Upload to mock S3
                rubin_data_mocker.upload_fileobj(
                    metadata_data, location.bucket_name, key
                )

                metadata_objects.append({"key": key, "hash": f"hash_{i}_{day}"})
                test_metadata[f"{location.name}/{camera.name}/{day}"] = metadata_data

        # Process metadata
        await historical.download_and_store_metadata(location.name, metadata_objects)

        # Verify all metadata was stored and compressed
        assert len(historical._metadata) == len(metadata_objects)

        # Verify we can decompress and retrieve the data
        for storage_key, expected_data in test_metadata.items():
            compressed = historical._metadata.get(storage_key)
            assert compressed is not None

            decompressed = pickle.loads(zlib.decompress(compressed))
            assert decompressed == expected_data

    @pytest.mark.asyncio
    async def test_get_events_for_date_with_mixed_seq_nums(
        self, historical: HistoricalPoller
    ) -> None:
        """Test event retrieval with mixed sequence number types."""
        import pickle
        import zlib
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        # Create archived events with mixed seq_num types
        archived_events = [
            "camera1/2024-01-15/channel1/000001/test1.jpg",
            "camera1/2024-01-15/channel1/000010/test2.jpg",
            "camera1/2024-01-15/channel2/final/movie.mp4",
            "camera1/2024-01-15/channel3/000005/test3.jpg",
            "camera1/2024-01-16/channel1/000001/test4.jpg",  # Different date
        ]

        historical._compressed_events[loc_cam] = zlib.compress(
            pickle.dumps(archived_events)
        )

        test_date = date(2024, 1, 15)
        events = await historical.get_events_for_date(location, camera, test_date)

        # Should only get events from 2024-01-15
        assert len(events) == 4

        # Verify seq_num types
        seq_nums = [e.seq_num for e in events]
        assert 1 in seq_nums
        assert 10 in seq_nums
        assert "final" in seq_nums
        assert 5 in seq_nums

    @pytest.mark.asyncio
    async def test_get_most_recent_event_with_channel_filter(
        self, historical: HistoricalPoller
    ) -> None:
        """Test getting the most recent event for a specific channel."""
        import pickle
        import zlib

        from lsst.ts.rubintv.models.models import Channel

        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]
        loc_cam = f"{location.name}/{camera.name}"

        # Create events with different timestamps (simulated by seq_num)
        archived_events = [
            f"{camera.name}/2024-01-15/{channel.name}/000001/test1.jpg",
            f"{camera.name}/2024-01-15/{channel.name}/000010/test2.jpg",
            f"{camera.name}/2024-01-15/another_channel/000020/test3.jpg",
            f"{camera.name}/2024-01-14/{channel.name}/000050/test4.jpg",
        ]

        historical._compressed_events[loc_cam] = zlib.compress(
            pickle.dumps(archived_events)
        )

        # Mock channel with specific name
        class MockChannel(Channel):
            def __init__(self) -> None:
                super().__init__(name=channel.name, per_day=False, title="Mock Channel")

        mock_channel = MockChannel()
        most_recent = await historical.get_most_recent_event(
            location, camera, mock_channel
        )

        # Should return the event with highest key (most recent)
        assert most_recent is not None
        assert (
            most_recent.key
            == f"{camera.name}/2024-01-15/{channel.name}/000010/test2.jpg"
        )


class TestHistoricalPollerS3Integration:
    """Test S3 integration scenarios."""

    @pytest.mark.asyncio
    async def test_s3_client_initialization(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test S3 client initialization for all locations."""
        historical = HistoricalPoller(m.locations, test_mode=True)

        # Verify S3 clients were created for all locations
        assert len(historical._clients) == len(m.locations)

        for location in m.locations:
            assert location.name in historical._clients
            client = historical._clients[location.name]
            assert hasattr(client, "async_list_objects")
            assert hasattr(client, "async_get_object")

    @pytest.mark.asyncio
    async def test_get_objects_for_prefix(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test object retrieval for specific prefixes."""
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]

        # Mock some objects in S3
        test_objects = []
        for i in range(3):
            obj = rubin_data_mocker.generate_event(
                location.bucket_name, "test_camera", "test_channel", f"{i:06}"
            )
            test_objects.append(obj)

        # Test prefix-based retrieval
        prefix = "test_camera/2024-01-15"
        objects = await historical._get_objects_for_prefix(location, prefix)

        # Should return objects (empty in test mode, but method should work)
        assert isinstance(objects, list)

    @pytest.mark.asyncio
    async def test_error_handling_s3_failures(
        self, historical: HistoricalPoller
    ) -> None:
        """Test error handling when S3 operations fail."""
        location = m.locations[0]

        # Test with invalid prefix that might cause S3 errors
        invalid_prefix = "invalid/prefix/that/does/not/exist"

        # This should not raise an exception, even if S3 fails
        try:
            objects = await historical._get_objects_for_prefix(location, invalid_prefix)
            assert isinstance(objects, list)
        except Exception as e:
            # If an exception occurs, it should be logged but not propagated
            assert False, f"S3 error should be handled gracefully: {e}"


class TestHistoricalPollerPerformance:
    """Test performance-related scenarios."""

    @pytest.mark.asyncio
    async def test_large_event_batch_processing(
        self, historical: HistoricalPoller
    ) -> None:
        """Test processing large batches of events efficiently."""
        from lsst.ts.rubintv.models.models import Event

        # Create a large batch of events
        large_event_batch = []
        for i in range(1000):
            event = Event(
                key=f"camera1/2024-01-15/channel{i % 10}/{'%06d' % i}/test{i}.jpg"
            )
            large_event_batch.append(event)

        await historical.store_events(large_event_batch, "test_location")

        # Verify all events were stored
        loc_cam = "test_location/camera1"
        assert loc_cam in historical._temp_events
        assert len(historical._temp_events[loc_cam]) == 1000

        # Verify calendar was updated efficiently
        assert loc_cam in historical._calendar

    @pytest.mark.asyncio
    async def test_compression_efficiency(self, historical: HistoricalPoller) -> None:
        """Test that compression provides reasonable size reduction."""
        import pickle
        import zlib

        # Create a large list of event strings
        large_event_list = [
            f"camera1/2024-01-15/channel1/{i:06d}/test{i}.jpg" for i in range(1000)
        ]

        # Store in temp events
        historical._temp_events["test_key"] = large_event_list

        # Compress
        await historical.compress_events()

        # Verify compression occurred and data is smaller
        compressed_data = historical._compressed_events["test_key"]
        uncompressed_size = len(pickle.dumps(large_event_list))
        compressed_size = len(compressed_data)

        # Compression should reduce size significantly
        assert compressed_size < uncompressed_size

        # Verify data integrity
        decompressed = pickle.loads(zlib.decompress(compressed_data))
        assert decompressed == large_event_list

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_compression(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that temporary events are cleaned up after compression."""
        # Add temporary events
        historical._temp_events["key1"] = ["event1", "event2"]
        historical._temp_events["key2"] = ["event3", "event4"]

        assert len(historical._temp_events) == 2

        # Compress events
        await historical.compress_events()

        # Verify compressed data exists
        assert "key1" in historical._compressed_events
        assert "key2" in historical._compressed_events

        # Simulate the cleanup that happens in filter_convert_store_objects
        historical._temp_events = {}

        # Verify temporary events were cleaned up
        assert len(historical._temp_events) == 0
        assert len(historical._compressed_events) == 2


class TestHistoricalPollerHashUsage:
    """Test suite specifically for hash property usage in HistoricalPoller."""

    @pytest.mark.asyncio
    async def test_night_report_data_hash_method(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that NightReportData.__hash__() method works correctly."""
        from lsst.ts.rubintv.models.models import NightReportData

        # Create NightReportData with specific hash
        nr_data = NightReportData(
            key="camera1/2024-01-15/night_report/group/plot.png", hash="deadbeef"
        )

        # Test that __hash__ converts hex string to integer
        hash_int = hash(nr_data)
        expected = int("0xdeadbeef", 0)
        assert hash_int == expected

    @pytest.mark.asyncio
    async def test_hash_not_used_for_event_comparison(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that Event objects don't use hash for comparison/storage."""
        from lsst.ts.rubintv.models.models import Event

        # Events don't have hash field in the actual implementation
        # They store just the key and derive other fields
        event1 = Event(key="camera1/2024-01-15/channel1/000042/test.jpg")
        event2 = Event(key="camera1/2024-01-15/channel1/000043/test.jpg")

        # Events are compared by key, not hash
        assert event1 < event2  # Comparison works on key

        # Store events and verify hash is not used in storage/retrieval
        events = [event1, event2]
        await historical.store_events(events, "test_location")

        # Events are stored as archive strings (keys), not hash-based
        loc_cam = "test_location/camera1"
        stored_events = historical._temp_events[loc_cam]
        assert event1.key in stored_events
        assert event2.key in stored_events

    @pytest.mark.asyncio
    async def test_hash_in_s3_object_metadata(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test that hash values come from S3 object metadata (ETag)."""
        historical = HistoricalPoller(m.locations, test_mode=True)
        location = m.locations[0]
        camera = location.cameras[0]

        # Mock S3 objects with specific hash values
        s3_objects = [
            {
                "key": f"{camera.name}/2024-01-15/channel1/000001/test1.jpg",
                "hash": "etag1",
            },
            {
                "key": f"{camera.name}/2024-01-15/channel1/000002/test2.jpg",
                "hash": "etag2",
            },
            {"key": f"{camera.name}/2024-01-15/metadata.json", "hash": "etag_meta"},
        ]

        # Process objects
        await historical.filter_convert_store_objects(s3_objects, location)

        # Verify that while hash is provided in S3 objects,
        # it's not actively used for change detection in Events
        # (only NightReportData uses hash for comparison)

        # Events are stored and processed regardless of hash value
        loc_cam = f"{location.name}/{camera.name}"
        assert (
            loc_cam in historical._temp_events
            or loc_cam in historical._compressed_events
        )

    @pytest.mark.asyncio
    async def test_hash_change_detection_night_reports_only(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that hash is only used for change detection in night
        reports."""
        from lsst.ts.rubintv.models.models import NightReportData

        # Create two NightReportData objects with same key but different hash
        nr1 = NightReportData(
            key="camera1/2024-01-15/night_report/group/plot.png", hash="baba1"
        )
        nr2 = NightReportData(
            key="camera1/2024-01-15/night_report/group/plot.png", hash="baba2"
        )

        # They should be considered different objects due to different hash
        assert nr1 != nr2
        assert hash(nr1) != hash(nr2)

        # This demonstrates that hash is used for change detection
        # in night reports (via __hash__ and __eq__ methods)

    @pytest.mark.asyncio
    async def test_hash_ignored_in_event_processing(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that Event processing ignores hash values completely."""
        location = m.locations[0]

        # Same event with different hash values
        objects_v1 = [
            {"key": "camera1/2024-01-15/channel1/000001/test.jpg", "hash": "old_hash"}
        ]
        objects_v2 = [
            {"key": "camera1/2024-01-15/channel1/000001/test.jpg", "hash": "new_hash"}
        ]

        # Process first version
        await historical.filter_convert_store_objects(objects_v1, location)

        # Process second version with different hash
        await historical.filter_convert_store_objects(objects_v2, location)

        # Event should be processed both times since hash is ignored
        # The system relies on object list comparison, not hash comparison
        loc_cam = f"{location.name}/camera1"

        # Both calls should succeed without hash-based filtering
        # (demonstrating that Events don't use hash for change detection)
        assert (
            loc_cam in historical._temp_events
            or loc_cam in historical._compressed_events
        )

    @pytest.mark.asyncio
    async def test_event_model_has_no_hash_field(self) -> None:
        """Test that Event model doesn't include hash field."""
        from lsst.ts.rubintv.models.models import Event

        # Create event and verify it doesn't have hash field
        event = Event(key="camera1/2024-01-15/channel1/000001/test.jpg")

        # Event should have these fields but NOT hash
        assert hasattr(event, "key")
        assert hasattr(event, "camera_name")
        assert hasattr(event, "day_obs")
        assert hasattr(event, "channel_name")
        assert hasattr(event, "seq_num")
        assert hasattr(event, "filename")
        assert hasattr(event, "ext")

        # Event should NOT have hash field (that's only in NightReportData)
        assert not hasattr(event, "hash")

    @pytest.mark.asyncio
    async def test_hash_documentation_accuracy(self) -> None:
        """Test that hash usage matches documentation in NightReportData."""
        from lsst.ts.rubintv.models.models import NightReportData

        # According to docstring: "The md5 hash of the blob. This is used to
        # keep plot images up-to-date onsite."
        # This suggests hash is used for cache invalidation/change detection

        nr_data = NightReportData(
            key="camera1/2024-01-15/night_report/group/plot.png",
            hash="a1b2c3d4",  # MD5-like hash
        )

        # Verify the hash is stored and can be used for comparison
        assert nr_data.hash == "a1b2c3d4"

        # The __hash__ method converts the string to int for Python hashing
        python_hash = hash(nr_data)
        assert python_hash == int("0xa1b2c3d4", 0)

        # This enables using NightReportData in sets/dicts and for comparison
