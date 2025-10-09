import datetime
from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models_helpers import all_objects_to_events
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


class TestHistoricalPollerEdgeCases:
    """Test edge cases and error handling for HistoricalPoller."""

    @pytest.mark.asyncio
    async def test_get_events_for_date_with_final_seq_num(
        self, historical: HistoricalPoller
    ) -> None:
        """Test handling events with 'final' sequence numbers."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]

        # Create events with both numeric and 'final' seq nums
        event_keys = [
            f"{camera.name}/2024-01-15/channel1/000042/test_file.jpg",
            f"{camera.name}/2024-01-15/channel1/final/final_image.jpg",
            f"{camera.name}/2024-01-16/channel1/000001/next_day.jpg",
        ]

        event_objs = [{"key": key, "hash": "hash"} for key in event_keys]

        events = await all_objects_to_events(event_objs)
        await historical.store_events_structured(locname=location.name, events=events)

        test_date = date(2024, 1, 15)
        retrieved_events = await historical.get_events_for_date(
            location, location.cameras[0], test_date
        )
        assert len(retrieved_events) == 2

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
