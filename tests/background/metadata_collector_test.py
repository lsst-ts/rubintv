import json
from datetime import timedelta
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
    return MetadataCollector(clients, m.locations)


class TestMetadataCollectorChangeDetection:
    @pytest.mark.asyncio
    async def test_changed_metadata_invalidates_only_changed_cache_entry(
        self, mock_s3_client: Any
    ) -> None:
        clear_s3_client_cache()
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"

        today = get_current_day_obs()
        date_changed = today.isoformat()
        date_unchanged = (today - timedelta(days=1)).isoformat()

        original_changed_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_changed,
            marker="changed-v1",
        )
        original_unchanged_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_unchanged,
            marker="unchanged-v1",
        )

        collector.register_metadata_ref(loc_cam, date_changed, original_changed_hash)
        collector.register_metadata_ref(
            loc_cam, date_unchanged, original_unchanged_hash
        )

        cached_changed = await collector.get_metadata_for_date(
            location, camera, date_changed
        )
        cached_unchanged = await collector.get_metadata_for_date(
            location, camera, date_unchanged
        )

        assert cached_changed is not None
        assert cached_unchanged is not None
        assert date_changed in collector._metadata_cache[loc_cam]
        assert date_unchanged in collector._metadata_cache[loc_cam]

        new_changed_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_changed,
            marker="changed-v2",
        )
        assert new_changed_hash != original_changed_hash

        await collector.check_for_changed_metadata()

        refs_by_date = {
            ref.date_str: ref.metadata_hash for ref in collector.metadata_refs[loc_cam]
        }
        assert refs_by_date[date_changed] == new_changed_hash
        assert refs_by_date[date_unchanged] == original_unchanged_hash

        assert date_changed not in collector._metadata_cache[loc_cam]
        assert date_unchanged in collector._metadata_cache[loc_cam]

        refreshed_metadata = await collector.get_metadata_for_date(
            location, camera, date_changed
        )
        assert refreshed_metadata is not None
        assert refreshed_metadata["0"]["marker"] == "changed-v2"
        assert date_changed in collector._metadata_cache[loc_cam]

        clear_s3_client_cache()

    @pytest.mark.asyncio
    async def test_unchanged_metadata_keeps_cache_entry(
        self, mock_s3_client: Any
    ) -> None:
        clear_s3_client_cache()
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"
        date_str = get_current_day_obs().isoformat()

        metadata_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_str,
            marker="stable-v1",
        )
        collector.register_metadata_ref(loc_cam, date_str, metadata_hash)

        cached = await collector.get_metadata_for_date(location, camera, date_str)
        assert cached is not None
        assert date_str in collector._metadata_cache[loc_cam]

        await collector.check_for_changed_metadata()

        assert date_str in collector._metadata_cache[loc_cam]
        refs_by_date = {
            ref.date_str: ref.metadata_hash for ref in collector.metadata_refs[loc_cam]
        }
        assert refs_by_date[date_str] == metadata_hash

        clear_s3_client_cache()

    @pytest.mark.asyncio
    async def test_changed_metadata_is_refetched_after_cache_invalidation(
        self, mock_s3_client: Any
    ) -> None:
        clear_s3_client_cache()
        mocker = RubinDataMocker(m.locations, s3_required=True, populate=False)
        collector = _build_metadata_collector()

        location = m.locations[0]
        camera = location.cameras[0]
        loc_cam = f"{location.name}/{camera.name}"
        date_str = get_current_day_obs().isoformat()

        original_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_str,
            marker="changed-v1",
        )
        collector.register_metadata_ref(loc_cam, date_str, original_hash)

        initial_metadata = await collector.get_metadata_for_date(
            location, camera, date_str
        )
        assert initial_metadata is not None
        assert initial_metadata["0"]["marker"] == "changed-v1"
        assert date_str in collector._metadata_cache[loc_cam]

        updated_hash = _put_metadata_object(
            mocker,
            location.bucket_name,
            camera.name,
            date_str,
            marker="changed-v2",
        )
        assert updated_hash != original_hash

        await collector.check_for_changed_metadata()

        assert date_str not in collector._metadata_cache[loc_cam]

        refreshed_metadata = await collector.get_metadata_for_date(
            location, camera, date_str
        )
        assert refreshed_metadata is not None
        assert refreshed_metadata["0"]["marker"] == "changed-v2"
        assert date_str in collector._metadata_cache[loc_cam]

        refs_by_date = {
            ref.date_str: ref.metadata_hash for ref in collector.metadata_refs[loc_cam]
        }
        assert refs_by_date[date_str] == updated_hash

        clear_s3_client_cache()
