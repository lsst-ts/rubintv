import uvicorn
from lsst.ts.rubintv.main import app


def run_rubintv() -> None:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="debug",
    )


if __name__ == "__main__":
    run_rubintv()
