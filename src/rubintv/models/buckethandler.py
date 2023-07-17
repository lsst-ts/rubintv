from abc import ABC, abstractmethod
from typing import Type

import boto3
from google.cloud import storage


class BucketHandlerInterface(ABC):
    @abstractmethod
    def list_objects(self, prefix: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_object(self, object_id: str) -> dict:
        raise NotImplementedError


class BucketHandlerMaker:
    def __init__(self, service_handle: str = "s3") -> None:
        self._bucket_cls: Type[BucketHandlerInterface]
        match service_handle:
            case "gcs":
                self._bucket_cls = GCSBucketHandler
            case _:
                self._bucket_cls = S3BucketHandler

    def get_bucket_handler(self, bucket_handle: str) -> BucketHandlerInterface:
        cls_name = self._bucket_cls.__name__
        constructor = globals()[cls_name]
        return constructor(bucket_handle)


class GCSBucketHandler(BucketHandlerInterface):
    """Concrete BucketHandler class for GCS Buckets.

    Parameters
    ----------
    BucketHandlerInterface : class
        The BucketHandler interface.
    """

    def __init__(self, bucket_handle: str) -> None:
        client = storage.Client()
        self.client = client
        self.bucket_handle = bucket_handle
        self.bucket = client.bucket(bucket_handle)

    def list_objects(self, prefix: str) -> list[dict]:
        blobs = self.bucket.list_blobs(prefix=prefix)
        blobs_list = [{"name": blob.name, "hash": blob.etag} for blob in blobs]
        return sorted(blobs_list, key=lambda b: b["name"])

    def get_object(self, object_id: str) -> dict:
        return self.bucket.get_blob(blob_name=object_id)


class S3BucketHandler(BucketHandlerInterface):
    """Concrete BucketHandler class for S3 Buckets.

    Parameters
    ----------
    BucketHandlerInterface : class
        The BucketHandler interface.
    """

    def __init__(self, bucket_handle: str) -> None:
        self.client = boto3.client("s3")
        self.bucket_handle = bucket_handle

    def list_objects(self, prefix: str) -> list:
        args = {
            "Bucket": self.bucket_handle,
            "Prefix": prefix,
            "StartAfter": prefix,
            "Delimiter": "/",
        }
        paginator = self.client.get_paginator("list_objects_v2")
        objects: list[dict] = []
        for page in paginator.paginate(**args):
            for content in page.get("Contents", ()):
                object = {}
                object["name"] = content["Key"]
                object["hash"] = content["ETag"]
                objects.append(object)
        return objects

    def get_object(self, object_id: str) -> dict:
        return self.client.get_object(Bucket=self.bucket_handle, Key=object_id)
