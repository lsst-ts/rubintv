import uvicorn
from lsst.ts.rubintv.main import app
from uvicorn.config import LOGGING_CONFIG


def run_rubintv() -> None:
    LOGGING_CONFIG["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"

    # ping timeout/interval added to prevent unhandled disconnects.
    # there will be a better/more understandable way of dealing with them.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        ws_ping_interval=60,
        ws_ping_timeout=120,
    )


if __name__ == "__main__":
    run_rubintv()
