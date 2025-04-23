import argparse

import uvicorn
from lsst.ts.rubintv.main import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RubinTV application.")
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Set the log level for the application.",
    )
    return parser.parse_args()


def run_rubintv(log_level: str = "info") -> None:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level=log_level,
    )


if __name__ == "__main__":
    args = parse_args()
    run_rubintv(log_level=args.log_level)
