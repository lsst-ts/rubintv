from lsst.ts.rubintv.s3client import S3Client


async def get_metadata_obj(key: str, s3_client: S3Client) -> dict:
    if data := await s3_client.async_get_object(key):
        return data
    else:
        return {}
