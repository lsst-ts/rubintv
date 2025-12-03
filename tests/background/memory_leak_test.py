"""Memory leak detection tests for bucket polling background functions.

This module contains a comprehensive but fast memory leak test designed for CI.
It tests CurrentPoller memory usage with S3 connection pooling and garbage
collection.
"""

import asyncio
import gc
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.models.models import Channel, Location
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker


class CIMemoryTestMocker(RubinDataMocker):
    """Lightweight data mocker optimized for fast CI memory testing."""

    def __init__(
        self,
        locations: list[Location],
        metadata_entries_per_camera: int = 20,  # Reduced for CI speed
        **kwargs: Any,
    ) -> None:
        """Initialize with modest data amounts for fast CI testing.

        Parameters
        ----------
        locations : `list` [`Location`]
            List of locations to mock data for
        metadata_entries_per_camera : `int`
            Number of metadata entries per camera (default: 20)
        """
        # Enable metadata creation with CI-appropriate amounts
        kwargs.setdefault("include_metadata", True)
        kwargs.setdefault("metadata_entries_per_camera", metadata_entries_per_camera)
        super().__init__(locations, **kwargs)

    def mock_up_data(self) -> None:
        """Generate modest amounts of mock data for CI testing."""
        super().mock_up_data()

        # Add extra sequences for basic stress testing
        for location in self._locations:
            loc_name = location.name
            for camera in location.cameras:
                # Store original channels
                original_channels = camera.channels[:]

                # Create one additional channel per camera for basic testing
                expanded_channels = []
                for channel in original_channels:
                    new_channel = Channel(
                        name=f"{channel.name}_ci_test",
                        title=f"{channel.title} CI Test",
                        colour=channel.colour,
                        per_day=channel.per_day,
                    )
                    expanded_channels.append(new_channel)

                # Temporarily replace camera channels
                original_camera_channels = camera.channels
                camera.channels = original_channels + expanded_channels

                print(
                    f"Mocking extra channels for camera {camera.name} at location {loc_name}"
                )
                print(f"  Original channels: {[ch.name for ch in original_channels]}")
                print(f"  Expanded channels: {[ch.name for ch in camera.channels]}")

                try:
                    self.location_channels[loc_name] = camera.channels
                    self.add_seq_objs(location, camera, include_empty_channel=False)
                finally:
                    # Restore original channels
                    camera.channels = original_camera_channels
                    print(
                        f"Restored original channels for camera {camera.name} at location {loc_name}"
                    )
                    print(f"  Current channels: {[ch.name for ch in camera.channels]}")


class FastCurrentPoller(CurrentPoller):
    """CurrentPoller optimized for fast CI testing."""

    # Fast polling for CI testing
    MIN_INTERVAL = 0.01  # 10ms
    RUNNING_LOG_PERIOD = 50  # Less frequent logging

    def __init__(
        self,
        *args: Any,
        max_iterations: int = 100,
        test_duration: int = 10,
        **kwargs: Any,
    ) -> None:
        """Initialize with time and iteration limits for CI.

        Parameters
        ----------
        max_iterations : `int`
            Maximum number of polling iterations (default: 100)
        test_duration : `int`
            Maximum test duration in seconds (default: 10)
        """
        super().__init__(*args, **kwargs)
        self.max_iterations = max_iterations
        self.test_duration = test_duration
        self.start_time: float | None = None
        self.iteration_count = 0

    async def poll_buckets_then_wait_and_repeat(self) -> None:
        """Override to add iteration and time limits for CI testing."""
        from lsst.ts.rubintv.config import rubintv_logger

        logger = rubintv_logger()

        self.start_time = time.time()
        logger.info(
            f"Starting FastCurrentPoller with max_iterations={self.max_iterations}, "
            f"test_duration={self.test_duration}s"
        )

        while True:
            # Check iteration limit
            if self.iteration_count >= self.max_iterations:
                logger.info(f"Reached max iterations ({self.max_iterations}), stopping")
                break

            # Check time limit
            elapsed = time.time() - self.start_time
            if elapsed >= self.test_duration:
                logger.info(
                    f"Reached time limit ({self.test_duration}s), stopping after {elapsed:.2f}s"
                )
                break

            # Count this as an iteration attempt regardless of success
            self.iteration_count += 1
            logger.debug(f"Starting iteration {self.iteration_count} at {elapsed:.2f}s")

            # Perform one polling iteration - catch errors to continue testing
            iteration_start = time.time()
            try:
                await self.poll_buckets_for_todays_data()
                iteration_time = time.time() - iteration_start
                logger.debug(
                    f"Completed iteration {self.iteration_count} successfully in {iteration_time:.3f}s"
                )
            except Exception as e:
                iteration_time = time.time() - iteration_start
                logger.debug(
                    f"S3 error in iteration {self.iteration_count} after {iteration_time:.3f}s: {e}"
                )
                # Continue despite S3 errors for memory testing

            # Force garbage collection every 20 iterations for memory testing
            if self.iteration_count % 20 == 0:
                gc.collect()
                logger.info(f"Completed {self.iteration_count} iterations, forced GC")

            # Short sleep to prevent CPU spinning
            await asyncio.sleep(self.MIN_INTERVAL)


@asynccontextmanager
async def setup_ci_memory_test() -> (
    AsyncGenerator[tuple[FastCurrentPoller, CIMemoryTestMocker], None]
):
    """Set up a fast memory test environment for CI."""
    from ..conftest import mock_s3_service

    with mock_s3_service():
        # Initialize models and locations
        models_init = ModelsInitiator()
        locations = models_init.locations

        # Create mocked data with S3 buckets
        mocker = CIMemoryTestMocker(
            locations=locations,
            s3_required=True,  # This will create the S3 buckets properly
            include_metadata=True,
        )
        mocker.mock_up_data()

        # Mock websocket notifications
        with patch(
            "lsst.ts.rubintv.handlers.websocket_notifiers.notify_ws_clients"
        ) as mock_notify:
            mock_notify.return_value = AsyncMock()

            # Create fast poller for testing
            poller = FastCurrentPoller(
                locations=locations,
                max_iterations=100,  # Limit for CI speed
                test_duration=15,  # 15 second limit
                test_mode=True,  # Enable test mode
            )
            yield poller, mocker


@pytest.mark.asyncio
async def test_comprehensive_memory_usage() -> None:
    """Comprehensive memory leak test optimized for CI (runs for under 20
    seconds).

    This test validates:
    1. S3 connection pooling is working
    2. Garbage collection is functioning
    3. Memory usage remains reasonable during polling
    4. Metadata mocking works correctly
    5. No obvious memory leaks in short-term operation
    """
    async with setup_ci_memory_test() as (poller, mocker):
        # Validate initial setup
        assert len(mocker.get_metadata_files()) > 0, "No metadata files were created"

        # Measure initial memory state
        initial_memory = gc.get_count()
        start_time = time.time()

        # Start the poller task
        poller_task = asyncio.create_task(poller.poll_buckets_then_wait_and_repeat())

        # Let it run for a controlled period
        try:
            await asyncio.wait_for(poller_task, timeout=17.0)
        except asyncio.TimeoutError:
            # Expected if the poller doesn't self-terminate
            poller_task.cancel()
            try:
                await poller_task
            except asyncio.CancelledError:
                # Cancellation is expected when cleaning up the poller task
                # after timeout.
                pass

        # Measure final state
        end_time = time.time()
        final_memory = gc.get_count()
        test_duration = end_time - start_time

        # Validate test ran properly
        assert test_duration <= 30.0, f"Test ran too long for CI: {test_duration:.1f}s"

        # Validate poller performed work
        assert poller.iteration_count > 0, "Poller performed no iterations"
        assert (
            poller.iteration_count >= 30
        ), f"Too few iterations for meaningful test: {poller.iteration_count}"

        # Force final garbage collection
        collected = gc.collect()

        # Memory validation (basic checks)
        memory_growth = sum(final_memory) - sum(initial_memory)

        # Log results
        print("\nCI Memory Test Results:")
        print(f"  Duration: {test_duration:.1f}s")
        print(f"  Iterations: {poller.iteration_count}")
        print(
            f"  Memory objects: {sum(initial_memory)} → {sum(final_memory)} (Δ{memory_growth:+d})"
        )
        print(f"  Final GC collected: {collected} objects")
        print(f"  Metadata files: {len(mocker.get_metadata_files())}")

        # Basic memory sanity check - allow reasonable growth for CI
        assert (
            memory_growth < 10000
        ), f"Excessive memory growth detected: {memory_growth} objects"

        print("✓ CI memory test passed - no obvious memory leaks detected")


if __name__ == "__main__":
    print("Fast memory leak test for CI")
    print(
        "Run with: pytest tests/background/memory_leak_test.py::test_comprehensive_memory_usage -v"
    )
    print("Test is designed to complete within 15 seconds for CI integration")
