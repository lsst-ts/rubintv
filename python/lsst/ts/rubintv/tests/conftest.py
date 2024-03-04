"""Test fixtures for rubintv tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncIterator, Tuple

import boto3
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv import main
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


@pytest_asyncio.fixture
async def mocked_app(
    aws_credentials: Any,
) -> AsyncIterator[Tuple[FastAPI, RubinDataMocker]]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    mock = mock_s3()
    mock.start()
    models = ModelsInitiator()
    mocker = RubinDataMocker(models.locations, s3_required=True)
    async with LifespanManager(main.app):
        yield main.app, mocker
        mock.stop()


@pytest_asyncio.fixture
async def mocked_client(
    mocked_app: Tuple[FastAPI, RubinDataMocker]
) -> AsyncIterator[Tuple[AsyncClient, RubinDataMocker]]:
    app, mocker = mocked_app
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000/") as client:
        yield client, mocker


@pytest.fixture
def mock_s3_client(aws_credentials: Any) -> Any:
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")
