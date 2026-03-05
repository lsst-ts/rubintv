"""Comprehensive tests for HistoricalPoller structured data storage and
retrieval.

These tests specifically validate:
1. Correct 3-level nested storage structure:
    _structured_events[loc_cam][date_str][channel]
2. Type compliance for StructuredData and ExtensionInfo
3. Input/output validation for make_structured_data and make_extension_info
    helpers
4. Full integration workflow from events to storage to retrieval
"""

from typing import Any, Iterator

import pytest
from lsst.ts.rubintv.background.background_helpers import (
    make_extension_info,
    make_structured_data,
)
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import Event
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..conftest import mock_s3_service
from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.fixture(scope="function")
def rubin_data_mocker(mock_s3_client: Iterator[Any]) -> Iterator[RubinDataMocker]:
    with mock_s3_service():
        mocker = RubinDataMocker(m.locations, s3_required=True)
        yield mocker


@pytest.fixture
def historical(rubin_data_mocker: RubinDataMocker) -> HistoricalPoller:
    return HistoricalPoller(m.locations)


class TestStructuredDataHelpers:
    """Test the helper functions for building structured data and extension
    info."""

    @pytest.mark.asyncio
    async def test_make_structured_data_single_channel(self) -> None:
        """Test make_structured_data with events from a single channel."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel1/000003/file3.jpg"),
        ]

        result = await make_structured_data(events)

        # Verify return type is StructuredData (dict[str, set[int|str]])
        assert isinstance(result, dict)
        assert "channel1" in result
        assert isinstance(result["channel1"], set)

        # Verify sequence numbers are correct type and values
        assert result["channel1"] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_make_structured_data_multiple_channels(self) -> None:
        """Test make_structured_data with events from multiple channels."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel2/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel2/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel2/000003/file3.jpg"),
        ]

        result = await make_structured_data(events)

        # Verify both channels present and correct
        assert len(result) == 2
        assert result["channel1"] == {1, 2}
        assert result["channel2"] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_make_structured_data_string_seq_num(self) -> None:
        """Test make_structured_data with 'final' seq_num."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel1/final/final_file.jpg"),
        ]

        result = await make_structured_data(events)

        # Verify set contains both int and str seq_nums
        assert result["channel1"] == {1, 2, "final"}

    @pytest.mark.asyncio
    async def test_make_structured_data_empty_list(self) -> None:
        """Test make_structured_data with empty event list."""
        events: list[Event] = []

        result = await make_structured_data(events)

        # Should return empty dict
        assert result == {}

    @pytest.mark.asyncio
    async def test_make_extension_info_single_extension(self) -> None:
        """Test make_extension_info with all events having same extension."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel1/000003/file3.jpg"),
        ]

        result = await make_extension_info(events)

        # Verify return type is ExtensionInfo
        assert isinstance(result, dict)
        assert "channel1" in result

        # Verify structure
        ext_dict = result["channel1"]
        assert "default" in ext_dict
        assert "exceptions" in ext_dict
        assert ext_dict["default"] == "jpg"
        assert ext_dict["exceptions"] == {}

    @pytest.mark.asyncio
    async def test_make_extension_info_mixed_extensions(self) -> None:
        """Test make_extension_info with mixed extensions."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel1/000003/file3.jpg"),
            Event(key="camera1/2024-01-15/channel1/000004/file4.fits"),
        ]

        result = await make_extension_info(events)

        # JPG should be default (3 vs 1)
        assert result["channel1"]["default"] == "jpg"
        # Fits should be in exceptions
        assert 4 in result["channel1"]["exceptions"]
        assert result["channel1"]["exceptions"][4] == "fits"

    @pytest.mark.asyncio
    async def test_make_extension_info_multiple_channels_mixed(self) -> None:
        """Test make_extension_info with multiple channels with different
        patterns."""
        events = [
            Event(key="camera1/2024-01-15/channel1/000001/file1.jpg"),
            Event(key="camera1/2024-01-15/channel1/000002/file2.jpg"),
            Event(key="camera1/2024-01-15/channel1/000003/file3.fits"),
            Event(key="camera1/2024-01-15/channel2/000001/file1.png"),
            Event(key="camera1/2024-01-15/channel2/000002/file2.png"),
            Event(key="camera1/2024-01-15/channel2/000003/file3.png"),
            Event(key="camera1/2024-01-15/channel2/000004/file4.jpg"),
        ]

        result = await make_extension_info(events)

        # Channel 1: jpg default (2 jpg vs 1 fits)
        assert result["channel1"]["default"] == "jpg"
        assert result["channel1"]["exceptions"] == {3: "fits"}

        # Channel 2: png default (3 png vs 1 jpg)
        assert result["channel2"]["default"] == "png"
        assert result["channel2"]["exceptions"] == {4: "jpg"}

    @pytest.mark.asyncio
    async def test_make_extension_info_empty_list(self) -> None:
        """Test make_extension_info with empty event list."""
        events: list[Event] = []

        result = await make_extension_info(events)

        # Should return empty dict
        assert result == {}


class TestHistoricalPollerStorageStructure:
    """Test HistoricalPoller storage structure and data retrieval."""

    @pytest.mark.asyncio
    async def test_storage_structure_is_3_level_nested(
        self, historical: HistoricalPoller
    ) -> None:
        """Verify _structured_events uses correct 3-level nesting.

        Structure should be:
        _structured_events[loc_cam][date_str][channel_name]
        where each value is a set[int|str] of sequence numbers.
        """
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000003/file3.jpg"),
        ]

        await historical.store_events_structured(events, location.name)

        # Verify structure exists
        loc_cam = f"{location.name}/{camera.name}"
        assert loc_cam in historical._structured_events
        assert "2024-01-15" in historical._structured_events[loc_cam]
        assert channel.name in historical._structured_events[loc_cam]["2024-01-15"]

        # Verify the innermost value is a set of int/str
        seq_nums = historical._structured_events[loc_cam]["2024-01-15"][channel.name]
        assert isinstance(seq_nums, set)
        assert seq_nums == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_storage_with_multiple_dates(
        self, historical: HistoricalPoller
    ) -> None:
        """Test storage maintains separate entries for different dates."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        events_date1 = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
        ]

        events_date2 = [
            Event(key=f"{camera.name}/2024-01-16/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-16/{channel.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-16/{channel.name}/000003/file3.jpg"),
        ]

        await historical.store_events_structured(events_date1, location.name)
        await historical.store_events_structured(events_date2, location.name)

        loc_cam = f"{location.name}/{camera.name}"
        structured = historical._structured_events[loc_cam]

        # Verify both dates present
        assert "2024-01-15" in structured
        assert "2024-01-16" in structured

        # Verify separate seq_nums for each date
        assert structured["2024-01-15"][channel.name] == {1, 2}
        assert structured["2024-01-16"][channel.name] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_storage_with_multiple_channels(
        self, historical: HistoricalPoller
    ) -> None:
        """Test storage maintains separate entries for different channels."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel1 = camera.channels[0]
        channel2 = camera.channels[1]

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000003/file3.jpg"),
        ]

        await historical.store_events_structured(events, location.name)

        loc_cam = f"{location.name}/{camera.name}"
        date_data = historical._structured_events[loc_cam]["2024-01-15"]

        # Verify both channels present with correct seq_nums
        assert channel1.name in date_data
        assert channel2.name in date_data
        assert date_data[channel1.name] == {1, 2}
        assert date_data[channel2.name] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_storage_with_multiple_cameras(
        self, historical: HistoricalPoller
    ) -> None:
        """Test storage maintains separate entries for different cameras."""
        location = m.locations[0]
        camera1 = location.cameras[0]
        camera2 = location.cameras[1]
        channel = camera1.channels[0]

        events_cam1 = [
            Event(key=f"{camera1.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera1.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
        ]

        # Create events for camera2 with same channel name
        events_cam2 = [
            Event(key=f"{camera2.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera2.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
            Event(key=f"{camera2.name}/2024-01-15/{channel.name}/000003/file3.jpg"),
        ]

        await historical.store_events_structured(events_cam1, location.name)
        await historical.store_events_structured(events_cam2, location.name)

        # Verify separate loc_cam entries
        loc_cam1 = f"{location.name}/{camera1.name}"
        loc_cam2 = f"{location.name}/{camera2.name}"

        assert loc_cam1 in historical._structured_events
        assert loc_cam2 in historical._structured_events

        # Verify correct seq_nums for each
        assert historical._structured_events[loc_cam1]["2024-01-15"][channel.name] == {
            1,
            2,
        }
        assert historical._structured_events[loc_cam2]["2024-01-15"][channel.name] == {
            1,
            2,
            3,
        }

    @pytest.mark.asyncio
    async def test_extension_info_storage_with_mixed_extensions(
        self, historical: HistoricalPoller
    ) -> None:
        """Test extension info storage correctly handles mixed extensions."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel1 = camera.channels[0]
        channel2 = camera.channels[1]

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000003/file3.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel1.name}/000004/file4.fits"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000001/file1.png"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000002/file2.png"),
            Event(key=f"{camera.name}/2024-01-15/{channel2.name}/000003/file3.fits"),
        ]

        await historical.store_events_structured(events, location.name)

        loc_cam = f"{location.name}/{camera.name}"
        channel1_key = f"{loc_cam}/2024-01-15/{channel1.name}"
        channel2_key = f"{loc_cam}/2024-01-15/{channel2.name}"

        # Verify channel1: jpg is default (3 jpg vs 1 fits)
        assert historical._channel_default_extensions[channel1_key] == "jpg"
        assert channel1_key in historical._extension_exceptions
        assert 4 in historical._extension_exceptions[channel1_key]
        assert historical._extension_exceptions[channel1_key][4] == "fits"

        # Verify channel2: png is default (2 png vs 1 fits)
        assert historical._channel_default_extensions[channel2_key] == "png"
        assert channel2_key in historical._extension_exceptions
        assert 3 in historical._extension_exceptions[channel2_key]
        assert historical._extension_exceptions[channel2_key][3] == "fits"

    @pytest.mark.asyncio
    async def test_retrieval_from_nested_structure(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that retrieval methods correctly access the nested
        structure."""
        from datetime import date

        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000003/file3.jpg"),
        ]

        await historical.store_events_structured(events, location.name)

        # Retrieve structured data
        structured_data = await historical.get_structured_data_for_date(
            location, camera, date(2024, 1, 15)
        )

        # Verify correct structure returned
        assert isinstance(structured_data, dict)
        assert channel.name in structured_data
        assert structured_data[channel.name] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_incremental_storage_accumulation(
        self, historical: HistoricalPoller
    ) -> None:
        """Test that multiple store operations correctly accumulate data."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        # First batch
        events_batch1 = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
        ]

        await historical.store_events_structured(events_batch1, location.name)

        loc_cam = f"{location.name}/{camera.name}"
        assert historical._structured_events[loc_cam]["2024-01-15"][channel.name] == {
            1,
            2,
        }

        # Second batch with new seq_nums
        events_batch2 = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000003/file3.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000004/file4.jpg"),
        ]

        await historical.store_events_structured(events_batch2, location.name)

        # Verify accumulated correctly
        assert historical._structured_events[loc_cam]["2024-01-15"][channel.name] == {
            1,
            2,
            3,
            4,
        }

    @pytest.mark.asyncio
    async def test_string_seq_num_in_storage(
        self, historical: HistoricalPoller
    ) -> None:
        """Test storage correctly handles 'final' string seq_nums."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/final/final_file.jpg"),
        ]

        await historical.store_events_structured(events, location.name)

        loc_cam = f"{location.name}/{camera.name}"
        seq_nums = historical._structured_events[loc_cam]["2024-01-15"][channel.name]

        # Verify set contains both int and str
        assert 1 in seq_nums
        assert "final" in seq_nums
        assert seq_nums == {1, "final"}

    @pytest.mark.asyncio
    async def test_type_validation_structured_data(self) -> None:
        """Verify StructuredData type is correctly enforced."""
        location = m.locations[0]
        camera = location.cameras[0]
        channel = camera.channels[0]

        historical = HistoricalPoller(m.locations)

        events = [
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000001/file1.jpg"),
            Event(key=f"{camera.name}/2024-01-15/{channel.name}/000002/file2.jpg"),
        ]

        await historical.store_events_structured(events, location.name)

        # Verify the structure matches StructuredData type:
        # dict[str, set[int | str]]
        structured_events = historical._structured_events
        assert isinstance(structured_events, dict)

        # Check loc_cam level
        # (StoredStructuredData = dict[str, dict[str, StructuredData]])
        for loc_cam_key, date_dict in structured_events.items():
            assert isinstance(loc_cam_key, str)
            assert isinstance(date_dict, dict)

            # Check date level
            for date_key, channel_dict in date_dict.items():
                assert isinstance(date_key, str)
                assert isinstance(channel_dict, dict)

                # Check channel level (should be StructuredData)
                for channel_key, seq_set in channel_dict.items():
                    assert isinstance(channel_key, str)
                    assert isinstance(seq_set, set)

                    # Check seq_nums are int or str
                    for seq_num in seq_set:
                        assert isinstance(seq_num, (int, str))
