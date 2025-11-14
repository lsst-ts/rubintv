from lsst.ts.rubintv.models.models import (
    CameraPageData,
    CurrentPageData,
    HistoricalPageData,
)


def test_camera_page_data_initialization() -> None:
    """Test initializing CameraPageData."""
    data = CameraPageData()
    assert data.per_day == {}
    assert data.nr_exists is False
    assert data.is_empty() is True

    # Test with data
    data.per_day = {"1": {}}
    assert data.is_empty() is False


def test_historical_page_data_initialization() -> None:
    """Test initializing HistoricalPageData."""
    data = HistoricalPageData()

    # Check base attributes are properly initialized
    assert data.per_day == {}
    assert data.metadata_exists is False
    assert data.nr_exists is False

    # Check subclass attributes
    assert data.structured_data == {}
    assert data.extension_info == {}
    assert data.is_empty() is True

    # Test with base data
    data.per_day = {"1": {}}
    assert data.is_empty() is False

    # Test with subclass data
    data = HistoricalPageData()
    data.structured_data = {"channel1": {1, 2, 3}}
    assert data.is_empty() is False


def test_current_page_data_initialization() -> None:
    """Test initializing CurrentPageData."""
    data = CurrentPageData()

    # Check base attributes are properly initialized
    assert data.per_day == {}
    assert data.metadata == {}
    assert data.nr_exists is False

    # Check subclass attributes
    assert data.channel_data == {}
    assert data.is_empty() is True

    # Test with subclass data
    data.channel_data = {1: {"channel1": {}}}
    assert data.is_empty() is False
