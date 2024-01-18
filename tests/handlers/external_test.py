"""Tests for the rubintv.handlers.external module and routes."""

from __future__ import annotations

from itertools import chain

import pytest
from bs4 import BeautifulSoup
from httpx import AsyncClient
from lsst.ts.rubintv.models.models import Location
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

m = ModelsInitiator()


@pytest.mark.asyncio
async def test_get_home(client: AsyncClient) -> None:
    """Test that home page has links to every location"""
    response = await client.get("/rubintv/")
    html = await response.aread()
    parsed = BeautifulSoup(html, "html.parser")
    locations = m.locations
    location_names = [loc.name for loc in locations]
    # find all nav links - there should be one for each location
    # (in the same order as defined in models_data.yaml)
    page_links = parsed.nav.find_all("a")
    page_slugs = [url.get("href").split("/")[-1] for url in page_links]
    assert location_names == page_slugs


@pytest.mark.asyncio
async def test_get_location(client: AsyncClient) -> None:
    """Test that location page has links to cameras"""
    location_name = "summit-usdf"
    location = find_first(m.locations, "name", location_name)
    assert type(location) is Location

    groups = location.camera_groups.values()
    camera_names = list(chain(*groups))
    response = await client.get(f"/rubintv/{location_name}")
    html = await response.aread()

    parsed = BeautifulSoup(html, "html.parser")
    page_links = list(parsed.select(".cameras a"))
    page_slugs = [url.get("href").split("/")[-1] for url in page_links]
    assert camera_names == page_slugs
