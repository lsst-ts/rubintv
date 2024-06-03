import os

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

ddv_router = APIRouter()
logger = structlog.get_logger("rubintv")


@ddv_router.get("{full_path:path}")
async def redirect_to_index(full_path: str, request: Request) -> FileResponse:
    # Check if the requested path is a file and exists in the static directory
    ddv_files_path = request.app.state.ddv_path
    return FileResponse(os.path.join(ddv_files_path, "index.html"))
