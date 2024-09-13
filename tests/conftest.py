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
from httpx import ASGITransport, AsyncClient
from lsst.ts.rubintv.main import create_app
from lsst.ts.rubintv.models.models_init import ModelsInitiator
from moto import mock_aws

from .mockdata import RubinDataMocker


@pytest.fixture(scope="module")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = (
        Path(__file__).parent.absolute() / "dummy_aws_credentials"
    )
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(moto_credentials_file_path)


@pytest.fixture(scope="function")
def mock_s3_client(aws_credentials: Any) -> Iterator[Any]:
    with mock_s3_service():
        yield boto3.client("s3", region_name="us-east-1")


@pytest_asyncio.fixture(scope="function")
async def mocked_client(
    mock_s3_client: Any,
) -> AsyncIterator[Tuple[AsyncClient, FastAPI, RubinDataMocker]]:
    app = create_app()
    models = ModelsInitiator()
    mocker = RubinDataMocker(models.locations, s3_required=True)
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000/"
        ) as client:
            yield client, app, mocker


@contextmanager
def mock_s3_service() -> Any:
    mock = mock_aws()
    mock.start()
    try:
        yield
    finally:
        mock.stop()
