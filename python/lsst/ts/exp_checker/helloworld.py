# this directory will be overwritten by the actual exp-checker app:
# https://github.com/lsst-sitcom/rubin_exp_checker

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_sub() -> dict[str, str]:
    return {"message": "Hello World!"}
