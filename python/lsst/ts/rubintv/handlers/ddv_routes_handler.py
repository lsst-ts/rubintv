import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

ddv_router = APIRouter()


@ddv_router.get("/{full_path:path}")
async def redirect_to_index(full_path: str, request: Request) -> Response:
    # Check if the requested path is a file and exists in the static directory
    ddv_files_path = request.app.state.ddv_path
    if os.path.isfile(os.path.join(ddv_files_path, full_path)):
        return await request.app.get("ddv-flutter").get_response(
            path=full_path, scope=request.scope
        )

    # If the path does not correspond to a file, serve index.html
    return FileResponse(os.path.join(ddv_files_path, "index.html"))
