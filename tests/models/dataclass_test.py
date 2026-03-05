from lsst.ts.rubintv.models.models import CameraPageData


def test_camera_page_data_initialization() -> None:
    """Test initializing CameraPageData with default values."""
    data = CameraPageData()
    assert data.per_day == {}
    assert data.nr_exists is False
    assert data.structured_data == {}
    assert data.extension_info == {}
    assert data.metadata == {}
    assert data.is_empty() is True


def test_camera_page_data_with_per_day() -> None:
    """Test CameraPageData is not empty when per_day has data."""
    data = CameraPageData(per_day={"channel1": {}})
    assert data.is_empty() is False


def test_camera_page_data_with_structured_data() -> None:
    """Test CameraPageData is not empty when structured_data has data."""
    data = CameraPageData(structured_data={"channel1": {1, 2, 3}})
    assert data.is_empty() is False


def test_camera_page_data_with_extension_info() -> None:
    """Test CameraPageData is not empty when extension_info has data."""
    data = CameraPageData(
        extension_info={"channel1": {"default": "jpg", "exceptions": {}}}
    )
    assert data.is_empty() is False


def test_camera_page_data_with_metadata() -> None:
    """Test CameraPageData is not empty when metadata has data."""
    data = CameraPageData(metadata={"key": "value"})
    assert data.is_empty() is False


def test_camera_page_data_with_night_report() -> None:
    """Test CameraPageData is empty when only nr_exists is True."""
    data = CameraPageData(nr_exists=True)
    assert data.is_empty() is True


def test_camera_page_data_combined_data() -> None:
    """Test CameraPageData with multiple data fields."""
    data = CameraPageData(
        per_day={"channel1": {}},
        structured_data={"channel1": {1, 2, 3}},
        extension_info={"channel1": {"default": "jpg", "exceptions": {}}},
        metadata={"key": "value"},
        nr_exists=True,
    )
    assert data.is_empty() is False
    assert data.nr_exists is True
    assert data.per_day == {"channel1": {}}
    assert data.structured_data == {"channel1": {1, 2, 3}}
    assert data.extension_info == {"channel1": {"default": "jpg", "exceptions": {}}}
    assert data.metadata == {"key": "value"}
