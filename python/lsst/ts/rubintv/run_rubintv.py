import uvicorn
from lsst.ts.rubintv.main import app
from uvicorn.config import LOGGING_CONFIG


def run_rubintv() -> None:
    LOGGING_CONFIG["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    run_rubintv()
