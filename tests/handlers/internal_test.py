"""Tests for the rubintv.handlers.internal module and routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv.config import config

from ..mockdata import RubinDataMocker


@pytest.mark.asyncio
async def test_get_index(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    client, app, mocker = mocked_client
    """Test ``GET /``"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == config.name
    assert isinstance(data["version"], str)
    assert isinstance(data["description"], str)
    assert isinstance(data["repository_url"], str)
    assert isinstance(data["documentation_url"], str)
