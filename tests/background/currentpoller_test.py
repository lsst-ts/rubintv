import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rubintv.background.currentpoller import CurrentPoller
from rubintv.models.models_init import ModelsInitiator

m = ModelsInitiator()


@pytest.fixture
def current_poller(setup_mock_s3_environment: Any) -> CurrentPoller:
    return CurrentPoller(m.locations)


@pytest.mark.asyncio
async def test_poll_buckets_for_todays_data(
    current_poller: CurrentPoller,
) -> None:
    # Mocking external functions
    with patch(
        "rubintv.models.models.get_current_day_obs", return_value="20210101"
    ) as mock_day_obs, patch(
        "rubintv.background.currentpoller.CurrentPoller.clear_all_data",
        new_callable=AsyncMock,
    ), patch(
        "rubintv.background.currentpoller.CurrentPoller.seive_out_metadata",
        new_callable=AsyncMock,
    ) as mock_metadata, patch(
        (
            "rubintv.background.currentpoller.CurrentPoller."
            "seive_out_night_reports"
        ),
        new_callable=AsyncMock,
    ) as mock_night_reports, patch(
        "rubintv.background.currentpoller.CurrentPoller."
        "process_channel_objects",
        new_callable=AsyncMock,
    ) as mock_process_objects:
        # Execute test
        try:
            # Run the method for a specified number of seconds, then timeout
            await asyncio.wait_for(
                current_poller.poll_buckets_for_todays_data(), timeout=0.1
            )
        except asyncio.TimeoutError:
            pass

        # Assertions
        assert mock_day_obs
        mock_metadata.assert_called()
        mock_night_reports.assert_called()
        mock_process_objects.assert_called()
        assert current_poller.completed_first_poll is True


@pytest.mark.asyncio
async def test_poll_buckets_for_today_process_and_store(
    current_poller: CurrentPoller,
) -> None:
    try:
        # Run the method for a specified number of seconds, then timeout
        await asyncio.wait_for(
            current_poller.poll_buckets_for_todays_data(), timeout=0.1
        )
    except asyncio.TimeoutError:
        # The timeout error is expected, so you can pass or handle it as needed
        pass
    print(current_poller._objects)


@pytest.mark.asyncio
async def test_clear_all_data(current_poller: CurrentPoller) -> None:
    try:
        # Run the method for a specified number of seconds, then timeout
        await asyncio.wait_for(
            current_poller.poll_buckets_for_todays_data(), timeout=0.1
        )
    except asyncio.TimeoutError:
        # The timeout error is expected, so you can pass or handle it as needed
        pass
    await current_poller.clear_all_data()
    assert current_poller._objects == {}
    assert current_poller._events == {}
    assert current_poller._metadata == {}
    assert current_poller._table == {}
    assert current_poller._per_day == {}
    assert current_poller._singles == {}
    assert current_poller._nr_metadata == {}
    assert current_poller._nr_reports == {}
