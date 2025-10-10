import datetime
from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
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
        assert historical._metadata_refs == {}
        assert historical._structured_events == {}
        assert historical._nr_metadata == {}
        assert historical._calendar == {}

    @pytest.mark.asyncio
    async def test_clear_all_data(self, historical: HistoricalPoller) -> None:
        """Test clearing all cached data."""
        # Populate some test data
        historical._have_downloaded = True
        historical._metadata_refs["test"] = {"2024-01-15"}
        historical._structured_events["test"] = {"2024-01-15": {"channel1": {1, 2}}}
        historical._nr_metadata["test"] = []
        historical._calendar["test"] = {}

        await historical.clear_all_data()

        assert historical._have_downloaded is False
        assert historical._metadata_refs == {}
        assert historical._structured_events == {}
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
        historical = HistoricalPoller(m.locations)
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
    async def test_complete_data_flow(self, rubin_data_mocker: RubinDataMocker) -> None:
        """Test the complete flow of data processing, storage and retrieval."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0].name

        # Create mock events with different extensions
        mock_events = []
        # Add jpg files
        for seq_num in range(1, 5):
            mock_events.append(
                {
                    "key": (
                        f"{camera.name}/2024-02-15/{channel}/{seq_num:06d}/"
                        f"{camera.name}_{channel}_{seq_num:06d}.jpg"
                    ),
                    "hash": f"hash{seq_num}",
                }
            )
        # Add fits files (different extension)
        for seq_num in range(5, 8):
            mock_events.append(
                {
                    "key": (
                        f"{camera.name}/2024-02-15/{channel}/{seq_num:06d}/"
                        f"{camera.name}_{channel}_{seq_num:06d}.fits"
                    ),
                    "hash": f"hash{seq_num}",
                }
            )
        # Add a 'final' seq_num
        mock_events.append(
            {
                "key": f"{camera.name}/2024-02-15/{channel}/final/{camera.name}_{channel}_final.jpg",
                "hash": "hash_final",
            }
        )

        # Add metadata object
        mock_events.append(
            {"key": f"{camera.name}/2024-02-15/metadata.json", "hash": "hash_meta"}
        )

        # Process the mock events
        await historical.filter_convert_store_objects(mock_events, location)

        # Verify data was stored correctly
        loc_cam = f"{location.name}/{camera.name}"
        assert loc_cam in historical._structured_events
        assert "2024-02-15" in historical._structured_events[loc_cam]
        assert channel in historical._structured_events[loc_cam]["2024-02-15"]

        # Check sequence numbers are stored
        seq_nums = historical._structured_events[loc_cam]["2024-02-15"][channel]
        assert len(seq_nums) == 8  # 7 numbered + 1 'final'
        assert all(i in seq_nums for i in range(1, 8))
        assert "final" in seq_nums

        # Verify extension handling
        channel_date_key = f"{loc_cam}/2024-02-15/{channel}"
        assert channel_date_key in historical._channel_default_extensions
        # JPG should be default (4 jpgs vs 3 fits)
        assert historical._channel_default_extensions[channel_date_key] == "jpg"

        # Check extension exceptions
        assert channel_date_key in historical._extension_exceptions
        assert (
            len(historical._extension_exceptions[channel_date_key]) == 3
        )  # fits files
        assert all(
            historical._extension_exceptions[channel_date_key][i] == "fits"
            for i in range(5, 8)
        )

        # Verify metadata was stored
        assert loc_cam in historical._metadata_refs
        assert "2024-02-15" in historical._metadata_refs[loc_cam]

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
        assert len(events) == 8

        # Verify extensions are correctly reconstructed
        jpg_events = [e for e in events if e.key.endswith(".jpg")]
        fits_events = [e for e in events if e.key.endswith(".fits")]
        assert len(jpg_events) == 5  # 4 numbered + final
        assert len(fits_events) == 3

        # Test channel data retrieval
        channel_data = await historical.get_channel_data_for_date(
            location, camera, test_date
        )
        assert len(channel_data) > 0

        # Test most recent day
        recent_day = await historical.get_most_recent_day(location, camera)
        assert recent_day == test_date

        # Test calendar flattening
        flat_calendar = historical.flatten_calendar(location, camera)
        assert "2024-02-15" in flat_calendar
        assert flat_calendar["2024-02-15"] == 7

    @pytest.mark.asyncio
    async def test_structured_event_storage_and_retrieval(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
        """Test the optimized storage and retrieval of structured event
        data."""
        historical = HistoricalPoller(m.locations)
        location = m.locations[0]
        camera = location.cameras[0]
        channel1 = camera.channels[0]
        channel2 = camera.channels[1]

        # Create events with varying extensions
        events = [
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel1.name}/000001/"
                    f"{camera.name}_{channel1.name}_000001.jpg"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel1.name}/000002/"
                    f"{camera.name}_{channel1.name}_000002.jpg"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel1.name}/000003/"
                    f"{camera.name}_{channel1.name}_000003.fits"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel1.name}/000004/"
                    f"{camera.name}_{channel1.name}_000004.jpg"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel2.name}/000001/"
                    f"{camera.name}_{channel2.name}_000001.png"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel2.name}/000002/"
                    f"{camera.name}_{channel2.name}_000002.png"
                )
            ),
            Event(
                key=(
                    f"{camera.name}/2024-03-10/{channel2.name}/000003/"
                    f"{camera.name}_{channel2.name}_000003.fits"
                )
            ),
        ]

        # Store the events
        await historical.store_events_structured(events, location.name)

        # Test extension storage optimization
        loc_cam = f"{location.name}/{camera.name}"
        channel1_key = f"{loc_cam}/2024-03-10/{channel1.name}"
        channel2_key = f"{loc_cam}/2024-03-10/{channel2.name}"

        # Channel 1 should have jpg as default (3 jpg vs 1 fits)
        assert historical._channel_default_extensions[channel1_key] == "jpg"
        # Channel 2 should have png as default (2 png vs 1 fits)
        assert historical._channel_default_extensions[channel2_key] == "png"

        # Check exceptions
        assert len(historical._extension_exceptions[channel1_key]) == 1
        assert historical._extension_exceptions[channel1_key][3] == "fits"

        assert len(historical._extension_exceptions[channel2_key]) == 1
        assert historical._extension_exceptions[channel2_key][3] == "fits"

        # Test event retrieval and reconstruction
        from datetime import date

        test_date = date(2024, 3, 10)

        # Get the structured data
        structured_data = await historical.get_structured_data_for_date(
            location, camera, test_date
        )
        assert channel1.name in structured_data
        assert channel2.name in structured_data
        assert len(structured_data[channel1.name]) == 4
        assert len(structured_data[channel2.name]) == 3

        # Test get_all_extensions_for_date
        extensions_info = await historical.get_all_extensions_for_date(
            location, camera, test_date
        )
        assert channel1.name in extensions_info
        assert channel2.name in extensions_info
        assert extensions_info[channel1.name]["default"] == "jpg"
        assert extensions_info[channel2.name]["default"] == "png"
        assert 3 in extensions_info[channel1.name]["exceptions"]

        # Test events reconstruction
        events = await historical.get_events_for_date_structured(
            location, camera, test_date
        )
        assert len(events) == 7

        # Check extensions are correctly reconstructed
        jpg_events = [e for e in events if e.key.endswith(".jpg")]
        fits_events = [e for e in events if e.key.endswith(".fits")]
        png_events = [e for e in events if e.key.endswith(".png")]

        assert len(jpg_events) == 3
        assert len(fits_events) == 2
        assert len(png_events) == 2

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
        await historical.filter_convert_store_objects(objects, location)

        # Verify metadata was stored
        loc_cam = f"{location.name}/{camera.name}"
        assert loc_cam in historical._metadata_refs
        assert date_str in historical._metadata_refs[loc_cam]

        # Verify night report data was stored
        assert location.name in historical._nr_metadata
        nr_data = [
            nr
            for nr in historical._nr_metadata[location.name]
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
    async def test_get_next_prev_event_with_structured_data(
        self, rubin_data_mocker: RubinDataMocker
    ) -> None:
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
        await historical.store_events_structured(events, location.name)

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
