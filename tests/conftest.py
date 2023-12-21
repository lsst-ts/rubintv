"""Test fixtures for rubintv tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from moto import mock_s3

from rubintv import main
from rubintv.mockdata import mock_up_data
from rubintv.models.models_init import ModelsInitiator


@pytest.fixture(scope="module")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = (
        Path(__file__).parent.absolute() / "dummy_aws_credentials"
    )
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(moto_credentials_file_path)


@pytest_asyncio.fixture
async def app(aws_credentials: Any) -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Wraps the application in a lifespan manager so that startup and shutdown
    events are sent during test execution.
    """
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    mock = mock_s3()
    mock.start()
    m = ModelsInitiator()
    mock_up_data(m.locations)
    async with LifespanManager(main.app):
        yield main.app
        mock.stop()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000/") as client:
        yield client
