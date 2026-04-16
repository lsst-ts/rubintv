import json
from typing import Any

import pytest
from lsst.ts.rubintv.background.metadata_collector import MetadataCollector
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_init import ModelsInitiator
from lsst.ts.rubintv.s3_connection_pool import (
    clear_s3_client_cache,
    get_shared_s3_client,
)

from ..mockdata import RubinDataMocker

m = ModelsInitiator()


def _put_metadata_object(
    mocker: RubinDataMocker,
    bucket_name: str,
    camera_name: str,
    date_str: str,
    marker: str,
) -> str:
    key = f"{camera_name}/{date_str}/metadata.json"
    payload = {
        "0": {
            "seq_num": 0,
            "marker": marker,
            "date_obs": date_str,
        }
    }
    mocker.s3_client.put_object(Bucket=bucket_name, Key=key, Body=json.dumps(payload))
    return mocker.get_obj_hash(bucket_name, key).strip('"')


def _build_metadata_collector() -> MetadataCollector:
    clients = {
        location.name: get_shared_s3_client(
            location.profile_name, location.bucket_name, location.endpoint_url
        )
        for location in m.locations
    }
    return MetadataCollector(clients, locations=m.locations)


class TestMetadataCollector:
    @pytest.mark.asyncio
    async def test_register_and_fetch_metadata(self, mock_s3_client: Any) -> None:
        clear_s3_client_cache()
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        date_str = get_current_day_obs().isoformat()

        _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_str,
            marker="v1",
        )

        collector.register_metadata_ref(loc_cam, date_str, "hash")
        assert date_str in {ref.date_str for ref in collector.metadata_refs[loc_cam]}

        metadata = await collector.get_metadata_for_date(location, camera, date_str)
        assert metadata is not None
        assert metadata["0"]["marker"] == "v1"
        assert date_str in collector._metadata_cache[loc_cam]

        clear_s3_client_cache()

    @pytest.mark.asyncio
    async def test_metadata_cached_on_second_request(self, mock_s3_client: Any) -> None:
        clear_s3_client_cache()
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"
        date_str = get_current_day_obs().isoformat()

        _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_str,
            marker="stable-v1",
        )
        collector.register_metadata_ref(loc_cam, date_str, "hash")

        cached = await collector.get_metadata_for_date(location, camera, date_str)
        assert cached is not None
        assert date_str in collector._metadata_cache[loc_cam]

        # Second request should hit cache
        cached_again = await collector.get_metadata_for_date(location, camera, date_str)
        assert cached_again is not None
        assert cached_again == cached

        clear_s3_client_cache()

    @pytest.mark.asyncio
    async def test_metadata_exists_for_date(self, mock_s3_client: Any) -> None:
        clear_s3_client_cache()
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"
        date_str = get_current_day_obs().isoformat()

        exists = await collector.metadata_exists_for_date(location, camera, date_str)
        assert exists is False

        collector.register_metadata_ref(loc_cam, date_str, "hash")

        exists = await collector.metadata_exists_for_date(location, camera, date_str)
        assert exists is True

        clear_s3_client_cache()
