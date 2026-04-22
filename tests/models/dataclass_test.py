from lsst.ts.rubintv.models.models import CameraPageData


def test_camera_page_data_initialization() -> None:
    """Test initializing CameraPageData."""
    data = CameraPageData()
    assert data.per_day == {}
    assert data.metadata == ""
    assert data.nr_exists is False
    assert data.structured_data == {}
    assert data.extension_info == {}
    assert data.is_empty() is True

    # Test with data
    data.per_day = {"1": {}}
    assert data.is_empty() is False


def test_camera_page_data_with_structured_data() -> None:
    """Test CameraPageData with structured data."""
    data = CameraPageData()
    data.structured_data = {"channel1": {1, 2, 3}}
    assert data.is_empty() is False


def test_camera_page_data_with_metadata() -> None:
    """Test CameraPageData with metadata."""
    data = CameraPageData()
    data.metadata = "compressed_data_string"
    # Even with metadata, if structured_data and per_day are empty,
    # is_empty should return True
    assert data.is_empty() is True
