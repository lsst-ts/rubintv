import uvicorn
from lsst.ts.rubintv.main import app


def run_rubintv() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    run_rubintv()
