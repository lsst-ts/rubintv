"""Tests for the rubintv.handlers.external module and routes."""

from __future__ import annotations

import asyncio
from itertools import chain

import pytest
from bs4 import BeautifulSoup
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import config
from lsst.ts.rubintv.models.models import Camera, Location, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker

m = ModelsInitiator()
app_name = config.name
day_obs = get_current_day_obs().isoformat()


@pytest.mark.asyncio
async def test_get_home(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that home page has links to every location"""
    client, _, _ = mocked_client
    response = await client.get(f"/{app_name}/")
    html = await response.aread()
    parsed = BeautifulSoup(html, "html.parser")
    locations = m.locations
    location_names = [loc.name for loc in locations if loc.is_teststand is False]
    # find all nav links - there should be one for each location
    # (in the same order as defined in models_data.yaml)
    navs = parsed.nav
    assert navs is not None
    page_links = navs.find_all("a")
    page_slugs = [url.get("href").split("/")[-1] for url in page_links]
    assert location_names == page_slugs


@pytest.mark.asyncio
async def test_get_location(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that location page has links to cameras"""
    client, _, _ = mocked_client
    location_name = "summit-usdf"
    location = find_first(m.locations, "name", location_name)
    assert type(location) is Location

    groups = location.camera_groups.values()
    camera_names = list(chain(*groups))
    response = await client.get(f"/{app_name}/{location_name}")
    html = await response.aread()

    parsed = BeautifulSoup(html, "html.parser")

    page_links = list(parsed.select(".cameras a"))
    page_urls = [url.get("href") for url in page_links]
    page_slugs = [url.split("/")[-1] for url in page_urls if type(url) is str]
    assert camera_names == page_slugs


@pytest.mark.asyncio
async def test_current_channels(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    client, app, mocker = mocked_client

    cp: CurrentPoller = app.state.current_poller
    hp: HistoricalPoller = app.state.historical
    cp.test_mode = True
    hp.test_mode = True
    while cp.completed_first_poll is False or hp._have_downloaded is False:
        await asyncio.sleep(0.1)

    for location in m.locations:
        for camera in location.cameras:
            loc_cam = f"{location.name}/{camera.name}"
            for seq_chan in camera.seq_channels():
                url = (
                    f"/{app_name}/{location.name}/{camera.name}"
                    f"/current/{seq_chan.name}"
                )
                response = await client.get(url)
                assert response.is_success

                html = await response.aread()
                parsed = BeautifulSoup(html, "html.parser")
                if mocker.empty_channel.get(loc_cam) == seq_chan.name:
                    assert parsed.select(".event-error")
                    assert not parsed.select(".event-info")
                # TODO: check for event-info (it's rendered via React- so
                # need to use a testing library that can handle React, like
                # Playwright or Selenium)
                # See DM-50301


@pytest.mark.asyncio
async def test_all_endpoints(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:

    client, app, _ = mocked_client

    locations = [loc.name for loc in m.locations]
    summit: Location = find_first(m.locations, "name", "summit-usdf")
    assert isinstance(summit, Location)

    all_cams = [f"{summit.name}/{cam.name}" for cam in summit.cameras]
    online_cams = [f"{summit.name}/{cam.name}" for cam in summit.cameras if cam.online]
    camera_historical = [f"{cam}/historical" for cam in online_cams]
    camera_dates = [f"{cam}/date/{day_obs}" for cam in online_cams]
    nr_current = [f"{cam}/night_report" for cam in online_cams]
    nr_dates = [f"{cam}/night_report/{day_obs}" for cam in online_cams]

    auxtel: Camera = find_first(summit.cameras, "name", "auxtel")
    assert isinstance(auxtel, Camera)

    channels = [
        f"{summit.name}/{auxtel.name}/current/{chan.name}"
        for chan in auxtel.seq_channels()
    ]

    page_rel_urls = [
        "",
        "admin",
        *all_cams,
        *locations,
        *camera_dates,
        *camera_historical,
        *nr_current,
        *nr_dates,
        *channels,
    ]

    hp: HistoricalPoller = app.state.historical
    while hp._have_downloaded is False:
        await asyncio.sleep(0.1)

    for url_frag in page_rel_urls:
        url = f"/{app_name}/{url_frag}"
        res = await client.get(url)
        if url.endswith("historical"):
            assert res.is_redirect
            continue
        assert res.is_success


@pytest.mark.asyncio
async def test_request_invalid_dates(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:

    client, _, _ = mocked_client

    summit: Location = find_first(m.locations, "name", "summit-usdf")
    assert isinstance(summit, Location)

    online_cams = [f"{summit.name}/{cam.name}" for cam in summit.cameras if cam.online]
    cam_date_words = [f"{cam}/date/not-a-date" for cam in online_cams if cam]
    cam_invalid_day = [f"{cam}/date/2000-49-10" for cam in online_cams if cam]
    cam_invalid_month = [f"{cam}/date/2000-27-13" for cam in online_cams if cam]
    cam_invalid_year = [f"{cam}/date/20001-27-12" for cam in online_cams if cam]
    cam_empty_year = [f"{cam}/date/1969-01-01" for cam in online_cams if cam]

    invalid_urls = [
        *cam_date_words,
        *cam_invalid_day,
        *cam_invalid_month,
        *cam_invalid_year,
    ]

    for url_frag in invalid_urls:
        url = f"/{app_name}/{url_frag}"
        res = await client.get(url)
        assert res.is_error

    for url_frag in cam_empty_year:
        url = f"/{app_name}/{url_frag}"
        res = await client.get(url)
        assert res.is_success


@pytest.mark.asyncio
async def test_slac_redirect(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that the SLAC redirect works"""
    client, _, _ = mocked_client
    # Test with no path
    response = await client.get(f"/{app_name}/slac")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/{app_name}/usdf")
    # Test with a trailing slash
    response = await client.get(f"/{app_name}/slac/")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/{app_name}/usdf/")
    # Test with a path
    response = await client.get(f"/{app_name}/slac/lsstcam")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/{app_name}/usdf/lsstcam")
    # Test with a path and no trailing slash
    response = await client.get(f"/{app_name}/slac/lsstcam/")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/{app_name}/usdf/lsstcam/")
    # Test with a deeper path
    response = await client.get(f"/{app_name}/slac/lsstcam/2023-10-01")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/{app_name}/usdf/lsstcam/2023-10-01")
