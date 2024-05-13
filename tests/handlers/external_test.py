"""Tests for the rubintv.handlers.external module and routes."""

from __future__ import annotations

import asyncio
from itertools import chain

import pytest
from bs4 import BeautifulSoup
from httpx import AsyncClient
from lsst.ts.rubintv.models.models import Location
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.mark.asyncio
async def test_get_home(mocked_client: tuple[AsyncClient, RubinDataMocker]) -> None:
    """Test that home page has links to every location"""
    client, mocker = mocked_client
    response = await client.get("/rubintv/")
    html = await response.aread()
    parsed = BeautifulSoup(html, "html.parser")
    locations = m.locations
    location_names = [loc.name for loc in locations]
    # find all nav links - there should be one for each location
    # (in the same order as defined in models_data.yaml)
    navs = parsed.nav
    assert navs is not None
    page_links = navs.find_all("a")
    page_slugs = [url.get("href").split("/")[-1] for url in page_links]
    assert location_names == page_slugs


@pytest.mark.asyncio
async def test_get_location(mocked_client: tuple[AsyncClient, RubinDataMocker]) -> None:
    """Test that location page has links to cameras"""
    client, mocker = mocked_client
    location_name = "summit-usdf"
    location = find_first(m.locations, "name", location_name)
    assert type(location) is Location

    groups = location.camera_groups.values()
    camera_names = list(chain(*groups))
    response = await client.get(f"/rubintv/{location_name}")
    html = await response.aread()

    parsed = BeautifulSoup(html, "html.parser")

    page_links = list(parsed.select(".cameras a"))
    page_urls = [url.get("href") for url in page_links]
    page_slugs = [url.split("/")[-1] for url in page_urls if type(url) is str]
    assert camera_names == page_slugs


# below is valid test when run in isolation but not after either of the two
# tests above. Commenting out to keep the test for future use.


@pytest.mark.asyncio
async def test_current_channels(
    mocked_client: tuple[AsyncClient, RubinDataMocker]
) -> None:
    """Test that location page has links to cameras"""
    client, mocker = mocked_client
    print("in test_current_channels")
    print(mocker.empty_channel)
    # allow historicaldata time to sort info
    await asyncio.sleep(0.2)
    for location in m.locations:
        for camera in location.cameras:
            loc_cam = f"{location.name}/{camera.name}"
            for seq_chan in camera.seq_channels():
                url = (
                    f"/rubintv/{location.name}/{camera.name}"
                    f"/current/{seq_chan.name}"
                )
                response = await client.get(url)

                assert response.status_code == 200

                html = await response.aread()
                parsed = BeautifulSoup(html, "html.parser")

                if mocker.empty_channel[loc_cam] == seq_chan.name:
                    assert parsed.select(".event-error")
                    assert not parsed.select(".event-info")
                else:
                    assert parsed.select(".event-info")
                    assert not parsed.select(".event-error")
