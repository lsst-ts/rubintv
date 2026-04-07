"""Metadata collection and caching for historical data."""

import asyncio
from collections import OrderedDict

from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import Camera, Location
from lsst.ts.rubintv.models.models_helpers import date_str_to_date
from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger(__name__)


class MetadataCollector:
    """Manages historical metadata collection with LRU caching and prefetching.

    Provides caching with LRU (Least Recently Used) eviction policy, background
    prefetching, and synchronization to prevent duplicate S3 fetches.
    """

    # Maximum days to cache metadata
    METADATA_CACHE_DAYS = 60

    def __init__(self, s3_clients: dict[str, S3Client]) -> None:
        """Initialize the metadata collector.

        Parameters
        ----------
        s3_clients : `dict`[`str`, `S3Client`]
            Dictionary mapping location names to S3 client instances.
        """
        self._s3_clients = s3_clients

        # Metadata refs tracking available dates for each loc_cam
        self._metadata_refs: dict[str, set[str]] = {}
        # Structure: {loc_cam: {date_str}}

        # Metadata cache using OrderedDict for LRU behavior
        self._metadata_cache: dict[str, OrderedDict[str, dict]] = {}
        # Structure: {loc_cam: OrderedDict({date_str: metadata_dict})}

        # Background prefetch control
        self._metadata_prefetch_task: asyncio.Task | None = None
        self._prefetch_paused = asyncio.Event()
        self._active_requests = 0
        self._request_lock = asyncio.Lock()

        # Per-key locks to prevent duplicate fetches
        self._fetch_locks: dict[str, asyncio.Lock] = {}

    @property
    def metadata_refs(self) -> dict[str, set[str]]:
        """Get the metadata refs dictionary."""
        return self._metadata_refs

    def register_metadata_ref(self, loc_cam: str, date_str: str) -> None:
        """Register that metadata exists for a location/camera/date
        combination.

        Parameters
        ----------
        loc_cam : `str`
            Location and camera identifier (format: "location/camera").
        date_str : `str`
            ISO format date string.
        """
        self._metadata_refs.setdefault(loc_cam, set()).add(date_str)

    async def get_metadata_for_date(
        self, location: Location, camera: Camera, date_str: str
    ) -> dict | None:
        """Get metadata for a specific date with caching.

        Fetches metadata from cache if available, otherwise retrieves from S3
        and caches the result. Uses per-key locks to prevent duplicate S3
        fetches.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.

        Returns
        -------
        metadata : `dict` | `None`
            The metadata dictionary, or None if not found or error occurred.
        """
        logger.debug(
            f"Requesting metadata for {location.name}/{camera.name} on {date_str}"
        )
        loc_cam = f"{location.name}/{camera.name}"

        if not self.metadata_exists_for_date(location, camera, date_str):
            logger.debug(f"Metadata does not exist for {loc_cam} on {date_str}")
            return None

        # Initialize cache for this loc_cam if needed
        if loc_cam not in self._metadata_cache:
            self._metadata_cache[loc_cam] = OrderedDict()

        cache = self._metadata_cache[loc_cam]

        # Check cache first
        if date_str in cache:
            # Move to end (mark as recently used)
            cache.move_to_end(date_str)
            return cache[date_str]

        # Use per-key lock to prevent duplicate fetches
        cache_key = f"{loc_cam}/{date_str}"
        if cache_key not in self._fetch_locks:
            self._fetch_locks[cache_key] = asyncio.Lock()

        async with self._fetch_locks[cache_key]:
            # Double-check cache after acquiring lock
            if date_str in cache:
                cache.move_to_end(date_str)
                return cache[date_str]

            # Track active request and pause prefetch if needed
            async with self._request_lock:
                self._active_requests += 1
                if self._active_requests == 1:
                    # First active request - pause prefetch
                    self._prefetch_paused.set()

            # Fetch from S3
            try:
                metadata = await self._fetch_metadata_from_s3(
                    location, camera, date_str
                )
                if metadata:
                    # Add to cache
                    cache[date_str] = metadata

                    # Maintain cache size limit
                    while len(cache) > self.METADATA_CACHE_DAYS:
                        cache.popitem(last=False)  # Remove oldest

                    # Move to end (mark as recently used)
                    cache.move_to_end(date_str)

                    logger.debug(f"Cached metadata for {loc_cam}/{date_str}")

                return metadata

            except Exception as e:
                logger.error(f"Failed to fetch metadata for {loc_cam}/{date_str}: {e}")
                return None
            finally:
                # Resume background prefetch when no active requests
                async with self._request_lock:
                    self._active_requests -= 1
                    if self._active_requests == 0:
                        # No more active requests - resume prefetch
                        self._prefetch_paused.clear()

    async def _fetch_metadata_from_s3(
        self,
        location: Location,
        camera: Camera,
        date_str: str,
    ) -> dict | None:
        """Fetch metadata from S3 for a specific date.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.

        Returns
        -------
        metadata : `dict` | `None`
            The metadata dictionary, or None if not found or error occurred.
        """
        client = self._s3_clients[location.name]
        key = f"{camera.name}/{date_str}/metadata.json"

        try:
            metadata = await client.async_get_object(key)
            return metadata
        except Exception:
            return None

    async def start_prefetch(self, locations: list[Location]) -> None:
        """Start background metadata prefetching.

        Parameters
        ----------
        locations : `list`[`Location`]
            List of location objects to prefetch metadata for.
        """
        if self._metadata_prefetch_task and not self._metadata_prefetch_task.done():
            self._metadata_prefetch_task.cancel()
            try:
                await self._metadata_prefetch_task
            except asyncio.CancelledError:
                pass

        self._prefetch_paused.clear()
        self._metadata_prefetch_task = asyncio.create_task(
            self._background_metadata_prefetch(locations)
        )

    async def _background_metadata_prefetch(self, locations: list[Location]) -> None:
        """Background task to prefetch metadata for the last 60 days.

        Parameters
        ----------
        locations : `list`[`Location`]
            List of location objects to prefetch metadata for.
        """
        try:
            logger.info("Starting background metadata prefetch")

            for location in locations:
                await self._prefetch_location_metadata(location)

            logger.info("Background metadata prefetch completed")

        except asyncio.CancelledError:
            logger.info("Metadata prefetch cancelled")
        except Exception as e:
            logger.error(f"Error in background metadata prefetch: {e}")

    async def _prefetch_location_metadata(self, location: Location) -> None:
        """Prefetch metadata for all cameras in a location.

        Parameters
        ----------
        location : `Location`
            The location object.
        """
        for camera in location.cameras:
            if not camera.online:
                continue

            loc_cam = f"{location.name}/{camera.name}"

            # Initialize cache for this loc_cam if needed
            if loc_cam not in self._metadata_cache:
                self._metadata_cache[loc_cam] = OrderedDict()

            cache = self._metadata_cache[loc_cam]

            # Get all available metadata dates for this camera, sorted newest
            # first
            available_dates: list[str] = []
            if loc_cam in self._metadata_refs:
                available_dates = sorted(
                    self._metadata_refs[loc_cam],
                    key=lambda d: date_str_to_date(d),
                    reverse=True,
                )

            # Prefetch up to last 60 found metadata files, skipping already
            # cached dates
            prefetch_count = 0
            for date_str in available_dates:
                # Pause prefetch if there are active requests
                while self._prefetch_paused.is_set():
                    await asyncio.sleep(0.1)

                if date_str in cache:
                    continue

                if prefetch_count >= self.METADATA_CACHE_DAYS:
                    break

                # Use per-key lock to prevent duplicate fetches
                cache_key = f"{loc_cam}/{date_str}"
                if cache_key not in self._fetch_locks:
                    self._fetch_locks[cache_key] = asyncio.Lock()

                async with self._fetch_locks[cache_key]:
                    # Double-check cache after acquiring lock
                    if date_str in cache:
                        continue

                    try:
                        metadata = await self._fetch_metadata_from_s3(
                            location, camera, date_str
                        )
                        if metadata:
                            # Add to cache (will be inserted at end due to
                            # OrderedDict)
                            cache[date_str] = metadata
                            # Move to end to mark as recently accessed
                            cache.move_to_end(date_str)

                            logger.debug(
                                f"Prefetched metadata for {loc_cam}/{date_str}"
                            )
                            prefetch_count += 1

                            # Small delay to prevent overwhelming S3
                            await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.debug(
                            f"Failed to prefetch metadata for {loc_cam}/{date_str}: {e}"
                        )

            if prefetch_count > 0:
                logger.info(f"Prefetched {prefetch_count} metadata files for {loc_cam}")

    async def shift_cache_for_new_day(self) -> None:
        """Shift the metadata cache when a new day rolls over."""
        for _, cache in self._metadata_cache.items():
            if len(cache) >= self.METADATA_CACHE_DAYS:
                # Remove oldest entries to make room
                while len(cache) >= self.METADATA_CACHE_DAYS:
                    cache.popitem(last=False)  # Remove oldest (FIFO)

    async def clear_cache(self) -> None:
        """Explicitly clear the metadata cache and refs."""
        logger.info("Clearing metadata cache and refs")
        self._metadata_refs.clear()
        for loc_cam in self._metadata_cache:
            self._metadata_cache[loc_cam].clear()
        self._fetch_locks.clear()

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        if self._metadata_prefetch_task and not self._metadata_prefetch_task.done():
            self._metadata_prefetch_task.cancel()
            try:
                await self._metadata_prefetch_task
            except asyncio.CancelledError:
                pass

    async def metadata_exists_for_date(
        self, location: Location, camera: Camera, date_str: str
    ) -> bool:
        """Check if metadata exists for a specific date.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.

        Returns
        -------
        exists : `bool`
            True if metadata exists, False otherwise.
        """
        loc_cam = f"{location.name}/{camera.name}"

        return (
            loc_cam in self._metadata_refs and date_str in self._metadata_refs[loc_cam]
        )
