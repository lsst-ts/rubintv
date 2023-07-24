import boto3


class S3BucketHandler:
    """Concrete BucketHandler class for S3 Buckets.

    Parameters
    ----------
    BucketHandlerInterface : class
        The BucketHandler interface.
    """

    _client = boto3.client("s3")

    def __init__(self, bucket_handle: str) -> None:
        self.bucket_handle = bucket_handle

    def list_objects(self, prefix: str) -> list[dict]:
        objects = []
        response = self._client.list_objects_v2(
            Bucket=self.bucket_handle, Prefix=prefix
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
                Bucket=self.bucket_handle,
                Prefix=prefix,
                ContinuationToken=response["NextContinuationToken"],
            )
        return objects

    def get_object(self, object_id: str) -> dict:
        return self._client.get_object(
            Bucket=self.bucket_handle, Key=object_id
        )
