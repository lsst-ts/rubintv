from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from lsst.ts.rubintv.s3client import S3Client

proxies_router = APIRouter()


@proxies_router.get(
    "/event_image/{location_name}/{camera_name}/{channel_name}/{filename}",
    response_class=StreamingResponse,
    name="event_image",
)
def proxy_image(
    location_name: str,
    camera_name: str,
    channel_name: str,
    filename: str,
    request: Request,
) -> StreamingResponse:
    try:
        to_remove = "_".join((camera_name, channel_name)) + "_"
        rest = filename.replace(to_remove, "")
        date_str, seq_ext = rest.split("_")
        seq_str, ext = seq_ext.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/{channel_name}/{seq_str}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    data_stream = s3_client.get_raw_object(key)
    return StreamingResponse(content=data_stream.iter_chunks())


@proxies_router.get(
    "/plot_image/{location_name}/{camera_name}/{group_name}/{filename}",
    response_class=StreamingResponse,
    name="plot_image",
)
def proxy_plot_image(
    location_name: str,
    camera_name: str,
    group_name: str,
    filename: str,
    request: Request,
) -> StreamingResponse:
    # auxtel_night_report_2023-08-16_Coverage_airmass

    try:
        to_remove = "_".join((camera_name, "night_report")) + "_"
        rest = filename.replace(to_remove, "")
        date_str = rest.split("_")[0]
        burn, ext = rest.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/night_report/{group_name}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    data_stream = s3_client.get_raw_object(key)
    return StreamingResponse(content=data_stream.iter_chunks())


@proxies_router.get(
    "/event_video/{location_name}/{camera_name}/{channel_name}/{filename}",
    response_class=StreamingResponse,
    name="event_video",
)
def proxy_video(
    location_name: str,
    camera_name: str,
    channel_name: str,
    filename: str,
    request: Request,
    range: str = Header(None),  # Get the Range header from the request
) -> StreamingResponse:
    try:
        to_remove = "_".join((camera_name, channel_name)) + "_"
        rest = filename.replace(to_remove, "")
        date_str, seq_ext = rest.split("_")
        seq_str, ext = seq_ext.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/{channel_name}/{seq_str}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    s3_request_headers = {}
    if range:
        byte_range = range.split("=")[1]
        s3_request_headers["Range"] = f"bytes={byte_range}"

    data = s3_client.get_movie(key, s3_request_headers)
    video = data["Body"]

    # Modify the response headers to signal that we accept byte range requests
    response_headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(data["ContentLength"]),
        "Content-Type": "video/mp4",
    }

    # If a range was provided, set the appropriate headers
    if range:
        end = data["ContentLength"] - 1
        start, _ = byte_range.split("-")
        response_headers["Content-Range"] = (
            f"bytes {start}-{end}/{data['ContentLength']}"
        )

    return StreamingResponse(
        content=video.iter_chunks(),
        headers=response_headers,
        status_code=206 if range else 200,
    )
