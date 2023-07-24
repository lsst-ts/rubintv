import asyncio

import boto3

from rubintv.models.models import Event, Location, get_current_day_obs


class BucketPoller:
    _client = boto3.client("s3")
    _current_lists: dict[str, dict[str, list | None]] = {}

    def __init__(self, locations: list[Location]) -> None:
        self.locations = locations
        # cam list is None by default or list if polled
        self._current_lists = {
            loc.name: {cam.name: None for cam in loc.cameras}
            for loc in locations
        }

    async def poll_buckets_for_todays_data(self) -> None:
        while True:
            current_day_obs = get_current_day_obs()
            for loc in self.locations:
                for camera in loc.cameras:
                    prefix = f"{camera.name}/{current_day_obs}"
                    objects = self.list_objects(loc.bucket_name, prefix)
                    if objects != self._current_lists[loc.name][camera.name]:
                        #  msg = {f"{loc.name}/{camera.name}", objects}
                        print(f"{loc.name}/{camera.name}")
                        print(objects)
                        #  await notify_current_camera_table_clients(msg)
                        self._current_lists[loc.name][camera.name] = objects
                    await asyncio.sleep(0.5)

    def list_objects(self, bucket_name: str, prefix: str) -> list[dict]:
        objects = []
        response = self._client.list_objects_v2(
            Bucket=bucket_name, Prefix=prefix
        )
        while True:
            for content in response.get("Contents", []):
                object = {}
                object["url"] = content["Key"]
                object["hash"] = content["ETag"].strip('"')
                objects.append(object)
            if "NextContinuationToken" not in response:
                break
            response = self._client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                ContinuationToken=response["NextContinuationToken"],
            )
        return objects

    def get_object(self, bucket_name: str, object_id: str) -> dict:
        return self._client.get_object(Bucket=bucket_name, Key=object_id)


def objects_to_events(objects: list[dict]) -> list[Event]:
    events = [Event(**object) for object in objects]
    return events
