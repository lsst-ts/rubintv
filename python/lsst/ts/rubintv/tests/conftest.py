"""Test fixtures for rubintv tests."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Tuple

import boto3
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv.main import create_app
from lsst.ts.rubintv.models.models_init import ModelsInitiator
from lsst.ts.rubintv.tests.mockdata import RubinDataMocker
from moto import mock_s3


@pytest.fixture(scope="module")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = (
        Path(__file__).parent.absolute() / "dummy_aws_credentials"
    )
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(moto_credentials_file_path)


@pytest_asyncio.fixture(scope="function")
async def mocked_app(
    aws_credentials: Any,
) -> AsyncIterator[Tuple[FastAPI, RubinDataMocker]]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    aws_test_creds = {
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
    with set_env_vars(aws_test_creds):
        mock = mock_s3()
        mock.start()
        models = ModelsInitiator()
        mocker = RubinDataMocker(models.locations, s3_required=True)
        app = create_app()
        async with LifespanManager(app):
            print(f"App id for this test: {id(app)}")
            yield app, mocker
        mocker.cleanup()
        mock.stop()


@pytest_asyncio.fixture(scope="function")
async def mocked_client(
    mocked_app: Tuple[FastAPI, RubinDataMocker]
) -> AsyncIterator[Tuple[AsyncClient, RubinDataMocker]]:
    app, mocker = mocked_app
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000/") as client:
        yield client, mocker


@pytest.fixture(scope="function")
def mock_s3_client(aws_credentials: Any) -> Any:
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")


@contextmanager
def set_env_vars(temp_vars: dict[str, str]) -> Iterator:
    old_values = {key: os.environ.get(key) for key in temp_vars}
    try:
        os.environ.update(temp_vars)
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                del os.environ[key]  # Remove the variable if it wasn't set before
            else:
                os.environ[key] = value  # Restore the original value
