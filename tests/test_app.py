"""Tests for the rubintv.app."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from bs4 import BeautifulSoup

from rubintv.app import create_app
from rubintv.models.models_assignment import locations

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


@pytest.mark.asyncio
async def test_successful_app_creation(aiohttp_client: TestClient) -> None:
    """Test the app stands up and displays home page. Uses minimal data loading"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    title = app["rubintv/site_title"]
    response = await client.get(f"{name}/")
    text = await response.text()
    assert title in text


@pytest.mark.asyncio
async def test_home_page(aiohttp_client: TestClient) -> None:
    """Test that home page has links to every location"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"{name}/")
    html = await response.text()
    parsed = BeautifulSoup(html, "html.parser")
    location_slugs = [loc.slug for loc in locations.values()]
    # find all nav links - there should be one for each location
    # (in the same order as defined in models_data.yaml)
    page_links = parsed.nav.find_all("a")
    page_slugs = [url.get("href").split("/")[-1] for url in page_links]
    assert location_slugs == page_slugs
