import uvicorn
from lsst.ts.rubintv.main import app

# TODO: Change-out this method for starting app in production:
# See DM-43635


def run_rubintv() -> None:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )


if __name__ == "__main__":
    run_rubintv()
