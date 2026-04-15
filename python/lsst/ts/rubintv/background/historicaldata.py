import asyncio
import gc
from datetime import date, timedelta
from time import time
from typing import TYPE_CHECKING

from lsst.ts.rubintv.background.background_helpers import get_next_previous_from_table
from lsst.ts.rubintv.background.metadata_collector import MetadataCollector
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import (
    notify_all_status_change,
    notify_ws_clients,
)
from lsst.ts.rubintv.models.models import (
    Camera,
    Channel,
    Event,
    ExtensionDict,
    Location,
    LocCamDateChan,
    LocCamKey,
    NightReport,
    NightReportData,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import (
    date_str_to_date,
    find_first,
    make_table_from_event_list,
    objects_to_ngt_report_data,
)
from lsst.ts.rubintv.s3_connection_pool import get_shared_s3_client

if TYPE_CHECKING:
    from lsst.ts.rubintv.background.currentpoller import CurrentPoller
    from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger()

type StructuredData = dict[LocCamKey, dict[date, dict[Channel, set[int | str]]]]
type ExtensionInfo = dict[LocCamDateChan, ExtensionDict]
type TransmissableExtInfo = dict[str, ExtensionDict]
type TransmissableStructuredData = dict[str, list[int | str]]


class HistoricalPoller:
    """Provide a cache of the historical data.
    This class downloads and stores historical data from S3 buckets for
    multiple locations and cameras. It maintains structured data for efficient
    retrieval of events, metadata, and night reports. It also supports
    integration of current data and notifies clients of day changes.
    """

    # re-polling period in seconds
    REPOLL_BUCKET_PERIOD = 60 * 60 * 12  # 12 hours
    REPOLL_YESTERDAY_PERIOD = 60 * 2  # 2 minutes

    def __init__(
        self,
        locations: list[Location],
        test_mode: bool = False,
        prefix_extra: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> None:
        self._clients: dict[str, S3Client] = {}
        self._locations = locations
        self._clients = {
            location.name: get_shared_s3_client(
                location.profile_name, location.bucket_name, location.endpoint_url
            )
            for location in locations
        }

        # Initialize metadata collector
        self._metadata_collector = MetadataCollector(self._clients, self._locations)

        self._structured_events: StructuredData = {}
        # Structure:
        # {(Location, Camera): {date: {Channel: {seq_num1, seq_num2, ...}}}}

        self._channel_default_extensions: dict[LocCamDateChan, str] = {}
        # Structure: {LocCamDateChan: "default_ext"}

        self._extension_exceptions: dict[LocCamDateChan, dict[int | str, str]] = {}
        # Structure: {LocCamDateChan: {seq_num: "different_ext"}}

        self._nr_metadata: dict[Location, list[NightReportData]] = {}
        self._calendar: dict[LocCamKey, dict[int, dict[int, dict[int, int]]]] = {}

        self._have_downloaded = False

        self.test_mode = test_mode
        self.prefix_extra = prefix_extra
        self._start_date = start_date
        self._end_date = end_date

        # Add lock for thread-safe access during updates
        self._data_lock = asyncio.Lock()

    async def clear_all_data(self) -> None:
        self._have_downloaded = False
        self._structured_events = {}
        self._channel_default_extensions = {}
        self._extension_exceptions = {}
        self._nr_metadata = {}
        self._calendar = {}
        await self._metadata_collector.clear_cache()
        # Force garbage collection after clearing large data structures
        gc.collect()
        logger.debug("Cleared all historical data and triggered garbage collection")

    async def trigger_reload_everything(self) -> None:
        """Trigger a full reload of all historical data."""
        await self.clear_all_data()

    async def run(self) -> None:
        while True:
            if not self._have_downloaded:
                logger.info("Starting initial historical data download")
                start_time = time()
                for location in self._locations:
                    await self._initialise_location_store(location)
                self._have_downloaded = True
                elapsed = time() - start_time
                logger.info(
                    "Completed initial historical data download",
                    elapsed_time_seconds=elapsed,
                )
                await notify_all_status_change(historical_busy=False)
                # Start background metadata prefetching
                await self._metadata_collector.start_prefetch(self._locations)
                logger.info(
                    "HistoricalPoller initial run completed",
                    total_elapsed_time_seconds=elapsed,
                )

            await asyncio.sleep(20)

            # Re-poll yesterday's data until main recheck period elapsed
            loop_start = time()
            while time() - loop_start < self.REPOLL_BUCKET_PERIOD:
                repoll_start = time()
                await self.repoll_yesterday()
                elapsed = time() - repoll_start
                if elapsed < self.REPOLL_YESTERDAY_PERIOD:
                    await asyncio.sleep(self.REPOLL_YESTERDAY_PERIOD - elapsed)

            await self.repoll_buckets_and_update()

    async def repoll_yesterday(self) -> None:
        """Re-poll just yesterday's data to catch any late arrivals."""
        logger.info("Starting re-poll of yesterday's data")
        start_time = time()

        yesterday = get_current_day_obs() - timedelta(days=1)
        for location in self._locations:
            for camera in location.cameras:
                if camera.online:
                    try:
                        new_objects = await self._get_objects_for_location_camera(
                            location,
                            camera,
                            prefix_extra=yesterday.isoformat(),
                        )
                        await self._update_if_changed(
                            location, camera, new_objects, yesterday
                        )
                    except Exception as e:
                        logger.error(
                            f"Error re-polling yesterday's data: {e}",
                            location=location.name,
                            camera=camera.name,
                        )

        await self._metadata_collector.check_for_changed_metadata(yesterday)
        elapsed = time() - start_time
        logger.info(
            "Completed re-poll of yesterday's data",
            elapsed_time_seconds=elapsed,
        )

    async def repoll_buckets_and_update(self) -> None:
        """Recheck buckets for changes and update structured data if
        differences are found."""
        logger.info("Starting bucket recheck for changes")
        start_time = time()

        for location in self._locations:
            try:
                await self._check_location_for_changes(location)
            except Exception as e:
                logger.error(f"Error checking location for changes: {e}")

        await self._metadata_collector.check_for_changed_metadata()

        elapsed = time() - start_time
        logger.info(
            "Completed bucket recheck",
            elapsed_time_seconds=elapsed,
        )

    async def _check_location_for_changes(self, location: Location) -> None:
        """Check a specific location for changes in bucket data."""
        for camera in location.cameras:
            if not camera.online:
                continue

            try:
                # Get current objects from bucket
                new_objects = await self._get_objects_for_location_camera(
                    location, camera, self.prefix_extra
                )

                # Compare with cached objects and update if different
                await self._update_if_changed(location, camera, new_objects)
            except Exception as e:
                logger.error(
                    f"Error checking camera for changes: {e}",
                    location=location.name,
                    camera=camera.name,
                )

    def _build_prefixes_for_camera(
        self,
        camera: Camera,
        prefix_extra: str = "",
    ) -> list[str]:
        """Build bucket prefixes for a camera."""
        return [camera.name + "/" + prefix_extra]

    async def _get_objects_for_location_camera(
        self,
        location: Location,
        camera: Camera,
        prefix_extra: str = "",
    ) -> list[dict[str, str]]:
        """Get objects from bucket for a specific camera."""
        objects = []
        prefixes = self._build_prefixes_for_camera(camera, prefix_extra)

        for prefix in prefixes:
            try:
                objects.extend(await self._get_objects_for_prefix(location, prefix))
            except Exception as e:
                logger.error(f"Error fetching prefix: {e}")

        return objects

    def _parse_structured_key(
        self, key: str, camera: Camera, day_obs: date | None = None
    ) -> tuple[Camera, date, Channel, int | str] | None:
        """Parse an S3 key into structured components using the expected
        format and return them as a tuple. If the key cannot be parsed,
        return None.

        Parameters
        ----------
        key : `str`
            S3 object key in format: camera/date/channel/seq_num/filename.ext
        camera : `Camera`
            The camera identifier.
        day_obs : `date` | `None`, optional
            The specific date to validate against, by default None.

        Returns
        -------
        `tuple`[`Camera`, `date`, `Channel`, `int` | `str`] | `None`
            Tuple of (camera, date, channel, seq_num) or None
            if key cannot be parsed.
        """
        parts = key.split("/")
        if len(parts) < 5:
            return None

        camera_name = parts[0]
        date_str = parts[1]
        channel_name = parts[2]
        seq_part = parts[3]

        # Validate camera name
        if camera_name != camera.name:
            logger.debug(
                "Camera name in key does not match expected camera",
                key=key,
                expected=camera.name,
            )
            return None

        # Parse and validate date
        try:
            parsed_date = date_str_to_date(date_str)
        except ValueError:
            logger.debug(
                "Date string in key is not a valid date",
                key=key,
                date_str=date_str,
            )
            return None

        # If day_obs provided, validate it matches
        if day_obs is not None and parsed_date != day_obs:
            logger.debug(
                "Date in key does not match expected date",
                key=key,
                expected=day_obs.isoformat(),
                actual=parsed_date.isoformat(),
            )
            return None

        # Validate channel exists for this camera
        channel = find_first(camera.channels, "name", channel_name)
        if channel is None:
            logger.debug(
                "Channel name in key does not match any known channel",
                key=key,
                channel=channel_name,
                expected_channels=[c.name for c in camera.channels],
            )
            return None

        # Parse seq_num (int or string like 'final')
        try:
            seq_num: int | str = int(seq_part)
        except ValueError:
            seq_num = seq_part

        return (camera, parsed_date, channel, seq_num)

    async def _update_if_changed(
        self,
        location: Location,
        camera: Camera,
        new_objects: list[dict[str, str]],
        day_obs: date | None = None,
    ) -> None:
        """Compare new objects with cached data and update only if changed."""
        new_keys_set = await self._parse_new_objects(new_objects, camera, day_obs)

        # Build cached keys from structured data
        cached_keys_set = await self._build_keys_from_structured_data(
            location, camera, day_obs
        )
        # Check for differences
        if new_keys_set != cached_keys_set:
            message = f"Changes detected for {location.name}/{camera.name}"
            if day_obs is not None:
                message += f" for {day_obs.isoformat()}"
            logger.info(
                message,
                location=location.name,
                camera=camera.name,
                date=day_obs.isoformat() if day_obs else None,
                added=len(new_keys_set - cached_keys_set),
                removed=len(cached_keys_set - new_keys_set),
            )
            # If there are changes, cache them.
            if new_objects:
                await self._ingest_objects(
                    location,
                    new_objects,
                    camera=camera,
                    day_obs=day_obs,
                    replace_night_reports=False,
                    notify_structured_updates=True,
                )
        else:
            message = f"No changes detected for {location.name}/{camera.name}"
            if day_obs is not None:
                message += f" on {day_obs.isoformat()}"
            logger.debug(
                message,
                location=location.name,
                camera=camera.name,
                date=day_obs.isoformat() if day_obs else None,
            )

    async def _build_keys_from_structured_data(
        self, location: Location, camera: Camera, day_obs: date | None = None
    ) -> set:
        """Build a set of keys from the current structured data for a specific
        date or all dates if day_obs is None.

        example of structured key: (camera_name, date_str, channel_name,
        seq_num)

        Parameters
        ----------
        location : `Location`
            The location identifier.
        camera : `Camera`
            The camera identifier.
        day_obs : `date` | `None`, optional
            The specific date to build keys for, by default None (build keys
            for all dates).

        Returns
        -------
        cached_keys_set : `set`
            A set of structured keys for the specified location and date(s).
        """
        loc_cam = (location, camera)
        cached_keys_set = set()
        if day_obs is not None:
            if (
                loc_cam in self._structured_events
                and day_obs in self._structured_events[loc_cam]
            ):
                cached_keys_set.update(
                    await self._build_keys_from_structured_data_for_date(
                        location, camera, day_obs
                    )
                )
        else:
            if loc_cam in self._structured_events:
                for day_obs in self._structured_events[loc_cam]:
                    cached_keys_set.update(
                        await self._build_keys_from_structured_data_for_date(
                            location, camera, day_obs
                        )
                    )
        return cached_keys_set

    async def _parse_new_objects(
        self,
        new_objects: list[dict[str, str]],
        camera: Camera,
        day_obs: date | None = None,
    ) -> set[tuple[Camera, date, Channel, int | str]]:
        """Parse new objects into structured data format."""
        # Parse new object keys to extract structured components
        new_keys_set: set[tuple[Camera, date, Channel, int | str]] = set()

        # Only process event objects (skip metadata and night_report)
        new_objects = (await self._split_objects_by_type(new_objects))["events"]

        for obj in new_objects:
            key = obj["key"]
            parsed = self._parse_structured_key(key, camera, day_obs)
            if parsed is not None:
                new_keys_set.add(parsed)
        return new_keys_set

    async def _build_keys_from_structured_data_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> set[tuple[Camera, date, Channel, int | str]]:
        """Build a set of keys from the current structured data for a specific
        date."""
        cached_keys_set: set[tuple[Camera, date, Channel, int | str]] = set()
        loc_cam = (location, camera)
        if (
            loc_cam in self._structured_events
            and day_obs in self._structured_events[loc_cam]
        ):
            for channel in self._structured_events[loc_cam][day_obs]:
                for seq_num in self._structured_events[loc_cam][day_obs][channel]:
                    struct_key = (camera, day_obs, channel, seq_num)
                    cached_keys_set.add(struct_key)
        return cached_keys_set

    async def _cache_structured_data(
        self,
        structured_data: StructuredData,
        extension_info: ExtensionInfo,
        location: Location | None = None,
        camera: Camera | None = None,
        day_obs: date | None = None,
    ) -> None:
        """Cache the structured data with thread-safe access. If location,
        camera, and day_obs are provided, only update that specific subset of
        the data.

        Parameters
        ----------
        structured_data : `StructuredData`
            The structured data to cache.
        extension_info : `ExtensionInfo`
            The extension information to cache.
        location : `Location` | `None`, optional
            The specific location to update, by default None (update all).
        camera : `Camera` | `None`, optional
            The specific camera to update, by default None (update all).
        day_obs : `date` | `None`, optional
            The specific date to update, by default None (update all).
        """
        async with self._data_lock:
            # Remove old data for the affected location/camera/date if it
            # exists.
            if location is not None and camera is not None:
                loc_cam = (location, camera)
                if day_obs is not None:
                    if (
                        loc_cam in self._structured_events
                        and day_obs in self._structured_events[loc_cam]
                    ):
                        del self._structured_events[loc_cam][day_obs]
                        await self._delete_calendar_section(location, camera, day_obs)
                else:
                    if loc_cam in self._structured_events:
                        del self._structured_events[loc_cam]
                        await self._delete_calendar_section(location, camera)
            # Store the new data
            if day_obs is not None:
                for loc_cam, date_channel_data in structured_data.items():
                    location, camera = loc_cam
                    if loc_cam not in self._structured_events:
                        self._structured_events[loc_cam] = {}
                    await self._delete_calendar_section(location, camera, day_obs)
                    if day_obs in date_channel_data:
                        self._structured_events[loc_cam][day_obs] = date_channel_data[
                            day_obs
                        ]
            else:
                # When day_obs is None, merge instead of replace to handle
                # streaming pages correctly
                await self._merge_structured_data_into_cache(
                    structured_data, extension_info
                )
                return

            # Update extension info
            for channel_date_key, ext_info in extension_info.items():
                self._channel_default_extensions[channel_date_key] = ext_info["default"]
                if channel_date_key in self._extension_exceptions:
                    del self._extension_exceptions[channel_date_key]
                if ext_info["exceptions"]:
                    self._extension_exceptions[channel_date_key] = ext_info[
                        "exceptions"
                    ]

            # update calendar with new dates
            for (loc, cam), date_channel_data in structured_data.items():
                for day_obs, chan_seq_nums in date_channel_data.items():
                    for _, seq_nums in chan_seq_nums.items():
                        seq_num = (
                            max(seq_nums)
                            if all(isinstance(seq_num, int) for seq_num in seq_nums)
                            else 0
                        )
                        int_seq_num = seq_num if isinstance(seq_num, int) else 0
                        self.add_to_calendar(loc, cam, day_obs, int_seq_num)

    async def _delete_calendar_section(
        self, location: Location, camera: Camera, day_obs: date | None = None
    ) -> None:
        """Delete a section of the calendar for a specific location, camera,
        and date. Only call from lock-protected methods to ensure thread
        safety.

        Parameters
        ----------

        location : `Location`
            The location identifier.
        camera : `Camera`
            The camera identifier.
        day_obs : `date` | `None`, optional
            The specific date to delete, by default None (delete all dates for
            this location/camera).
        """
        loc_cam = (location, camera)
        if loc_cam in self._calendar:
            if day_obs is not None:
                year, month, day = day_obs.year, day_obs.month, day_obs.day
                if (
                    year in self._calendar[loc_cam]
                    and month in self._calendar[loc_cam][year]
                    and day in self._calendar[loc_cam][year][month]
                ):
                    del self._calendar[loc_cam][year][month][day]
                    # Clean up empty nested dictionaries
                    if not self._calendar[loc_cam][year][month]:
                        del self._calendar[loc_cam][year][month]
                    if not self._calendar[loc_cam][year]:
                        del self._calendar[loc_cam][year]
            else:
                del self._calendar[loc_cam]

    async def _filter_only_events(
        self, objects: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """Filter the list of objects to only include event objects."""
        return (await self._split_objects_by_type(objects))["events"]

    async def _split_objects_by_type(
        self, objects: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Split bucket objects by data type."""
        metadata_objs = [o for o in objects if "metadata.json" in o["key"]]
        n_report_objs = [o for o in objects if "night_report" in o["key"]]
        event_objs = [
            o
            for o in objects
            if "metadata.json" not in o["key"] and "night_report" not in o["key"]
        ]
        return {
            "events": event_objs,
            "metadata": metadata_objs,
            "night_reports": n_report_objs,
        }

    async def _merge_night_report_metadata(
        self, location: Location, night_report_data: list[NightReportData]
    ) -> None:
        """Merge incoming night report metadata into cache by unique key."""
        if not night_report_data:
            return

        existing = self._nr_metadata.get(location, [])
        by_key = {item.key: item for item in existing}
        for item in night_report_data:
            by_key[item.key] = item
        self._nr_metadata[location] = list(by_key.values())

    async def _ingest_objects(
        self,
        location: Location,
        objects: list[dict[str, str]],
        camera: Camera | None = None,
        day_obs: date | None = None,
        replace_night_reports: bool = False,
        notify_structured_updates: bool = False,
    ) -> None:
        """Shared ingest pipeline for event, metadata, and night report
        objects."""
        logger.info(
            "Ingesting objects for location",
            location=location.name,
            camera=camera.name if camera else None,
            date=day_obs.isoformat() if day_obs else None,
            total_objects=len(objects),
        )
        object_groups = await self._split_objects_by_type(objects)

        metadata_objs = object_groups["metadata"]
        n_report_objs = object_groups["night_reports"]
        event_objs = object_groups["events"]

        night_report_data = await objects_to_ngt_report_data(n_report_objs)
        if replace_night_reports:
            self._nr_metadata[location] = night_report_data
        else:
            await self._merge_night_report_metadata(location, night_report_data)

        await self.store_metadata_dates(location, metadata_objs)

        if event_objs:
            await self._convert_and_cache_structured_data(
                event_objs,
                location,
                camera,
                day_obs,
                notify_clients=notify_structured_updates,
            )

    async def _convert_and_cache_structured_data(
        self,
        new_objects: list[dict[str, str]],
        location: Location,
        camera: Camera | None,
        day_obs: date | None = None,
        notify_clients: bool = True,
    ) -> None:
        """Convert new objects to structured data and cache it."""
        # Filter to only event objects
        event_objects = await self._filter_only_events(new_objects)
        # Convert and build temporary structured data (no lock needed)
        temp_structured, temp_extension_info = (
            await self._convert_objects_to_structured(event_objects, location)
        )

        await self._cache_structured_data(
            temp_structured, temp_extension_info, location, camera, day_obs
        )

        if notify_clients and camera is not None:
            await self._notify_clients_of_structured_data_update(
                location, camera, day_obs, temp_structured, temp_extension_info
            )

    async def _notify_clients_of_structured_data_update(
        self,
        location: Location,
        camera: Camera,
        day_obs: date | None,
        structured_data: StructuredData,
        extension_info: ExtensionInfo,
    ) -> None:
        """Notify clients of structured data update for a specific location,
        camera, and date."""
        if day_obs is None:
            effected_days = list(structured_data.get((location, camera), {}).keys())
        else:
            effected_days = [day_obs]
        for day in effected_days:
            transmissable_structured_data = (
                await self._make_structured_data_transmissable(structured_data, day)
            )
            # Extract extension info for the specific day, keyed by channel
            # name
            transmissable_extension_info = self._make_extension_info_transmissable(
                extension_info, location, camera, day
            )
            await notify_ws_clients(
                service=Service.HISTORICALDATAUPDATE,
                message_type=MessageType.HISTORICAL_STRUCTURED_DATA,
                loc_cam="{}/{}".format(location.name, camera.name),
                payload={
                    "date": day.isoformat(),
                    "structuredData": transmissable_structured_data,
                    "extensionInfo": transmissable_extension_info,
                },
            )

    def _build_extension_info(
        self, channel_date_groups: dict[LocCamDateChan, dict[int | str, str]]
    ) -> tuple[dict[LocCamDateChan, str], dict[LocCamDateChan, dict[int | str, str]]]:
        """Helper to build extension info from seq_num to extension mapping.

        Parameters
        ----------
        channel_date_groups : dict
            Mapping of (location, camera, day_obs, channel) to dict of
            seq_num -> extension strings

        Returns
        -------
        tuple
            (temp_extensions, temp_exceptions) dicts
        """
        temp_extensions: dict[LocCamDateChan, str] = {}
        temp_exceptions: dict[LocCamDateChan, dict[int | str, str]] = {}

        for channel_date_key, seq_num_to_ext in channel_date_groups.items():
            if not seq_num_to_ext:
                continue

            # Count extension occurrences
            extension_counts: dict[str, int] = {}
            for ext in seq_num_to_ext.values():
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

            if extension_counts:
                default_ext = max(extension_counts.items(), key=lambda x: x[1])[0]
                temp_extensions[channel_date_key] = default_ext

                # Track exceptions (extensions different from default)
                exceptions: dict[int | str, str] = {}
                for seq_num, ext in seq_num_to_ext.items():
                    if ext != default_ext:
                        exceptions[seq_num] = ext
                if exceptions:
                    temp_exceptions[channel_date_key] = exceptions

        return temp_extensions, temp_exceptions

    async def _convert_objects_to_structured(
        self, event_objects: list[dict[str, str]], location: Location
    ) -> tuple[StructuredData, ExtensionInfo]:
        """Convert objects to structured data using existing key parser.

        Uses _parse_structured_key to parse S3 keys directly without
        creating Event objects, which is much faster.

        Returns a dictionary with the same structure as _structured_events
        that can be merged in atomically under the lock.
        """
        # Initialize accumulators
        temp_structured: StructuredData = {}
        channel_date_groups: dict[LocCamDateChan, dict[int | str, str]] = (
            {}
        )  # Map seq_num to ext

        # Process directly without Event object creation
        # Batch the processing for efficiency
        batch_size = 5000
        batches = [
            event_objects[i : i + batch_size]
            for i in range(0, len(event_objects), batch_size)
        ]

        for batch in batches:
            for obj in batch:
                key = obj.get("key", "")

                # Extract ext from key
                # (format: camera/date/channel/seq_num/filename.ext)
                parts = key.rsplit(".", 1)
                if len(parts) != 2:
                    continue
                ext = parts[1]

                # Use existing parser to get camera, date, channel, seq_num
                camera_name = key.split("/")[0] if "/" in key else None
                if not camera_name:
                    continue

                camera = find_first(location.cameras, "name", camera_name)
                if not camera:
                    continue

                # Parse using existing method
                parse_result = self._parse_structured_key(key, camera)
                if not parse_result:
                    continue

                camera_obj, day_obs, channel, seq_num = parse_result

                channel_date_key: LocCamDateChan = (
                    location,
                    camera_obj,
                    day_obs,
                    channel,
                )
                loc_cam = (location, camera_obj)

                if loc_cam not in temp_structured:
                    temp_structured[loc_cam] = {}
                if day_obs not in temp_structured[loc_cam]:
                    temp_structured[loc_cam][day_obs] = {}
                if channel not in temp_structured[loc_cam][day_obs]:
                    temp_structured[loc_cam][day_obs][channel] = set()

                temp_structured[loc_cam][day_obs][channel].add(seq_num)

                if channel_date_key not in channel_date_groups:
                    channel_date_groups[channel_date_key] = {}
                channel_date_groups[channel_date_key][seq_num] = ext

        # Build extension info using helper
        temp_extensions, temp_exceptions = self._build_extension_info(
            channel_date_groups
        )

        extension_info: ExtensionInfo = {}
        for key, default_ext in temp_extensions.items():
            extension_info[key] = {
                "default": default_ext,
                "exceptions": temp_exceptions.get(key, {}),
            }

        return temp_structured, extension_info

    async def _merge_structured_data_into_cache(
        self, structured_data: StructuredData, extension_info: ExtensionInfo
    ) -> None:
        """Merge structured event and extension data into in-memory cache."""
        for (location, camera), date_channel_data in structured_data.items():
            loc_cam = (location, camera)
            if loc_cam not in self._structured_events:
                self._structured_events[loc_cam] = {}
            for day_obs, channel_data in date_channel_data.items():
                if day_obs not in self._structured_events[loc_cam]:
                    self._structured_events[loc_cam][day_obs] = {}
                for channel, seq_nums in channel_data.items():
                    existing = self._structured_events[loc_cam][day_obs].setdefault(
                        channel, set()
                    )
                    existing.update(seq_nums)

        for channel_date_key, ext_info in extension_info.items():
            self._channel_default_extensions[channel_date_key] = ext_info["default"]
            if channel_date_key in self._extension_exceptions:
                del self._extension_exceptions[channel_date_key]
            if ext_info["exceptions"]:
                self._extension_exceptions[channel_date_key] = ext_info["exceptions"]

        for (loc, cam), date_channel_data in structured_data.items():
            for day_obs, chan_seq_nums in date_channel_data.items():
                for _, seq_nums in chan_seq_nums.items():
                    seq_num = (
                        max(seq_nums)
                        # squashes non-int seq_nums to 0 for calendar purposes
                        # as they only exist in per-day channels
                        if all(isinstance(seq_num, int) for seq_num in seq_nums)
                        else 0
                    )
                    int_seq_num = seq_num if isinstance(seq_num, int) else 0
                    self.add_to_calendar(loc, cam, day_obs, int_seq_num)

    async def clear_metadata_cache(self) -> None:
        """Explicitly clear the metadata cache (for testing or manual
        resets)"""
        await self._metadata_collector.clear_cache()

    async def integrate_todays_data(self, current_poller: "CurrentPoller") -> None:
        """Integrate today's data into the historical store."""
        try:
            logger.info("Integrating today's data from CurrentPoller")

            for location in self._locations:
                for camera in location.cameras:
                    if not camera.online:
                        continue

                    # Get today's events from CurrentPoller
                    events = await current_poller.get_current_events(
                        location.name, camera
                    )
                    if events:
                        # Acquire lock before modifying structured data
                        async with self._data_lock:
                            await self.store_events_structured(events, location)

                    # Get today's metadata from CurrentPoller
                    metadata = await current_poller.get_current_metadata(
                        location.name, camera
                    )
                    if metadata:
                        hash = await current_poller.get_latest_metadata_hash(
                            location.name, camera
                        )
                        today = current_poller._last_day_obs
                        self._metadata_collector.register_metadata_ref(
                            f"{location.name}/{camera.name}", today.isoformat(), hash
                        )
                        self.add_to_calendar(location, camera, today, 0)

                    # Get today's night reports from CurrentPoller
                    night_report = await current_poller.get_current_night_report(
                        location.name, camera.name
                    )
                    if night_report != NightReport():
                        self._nr_metadata.setdefault(location, []).extend(
                            night_report.plots if night_report.plots else []
                        )

                    await self._metadata_collector.shift_cache_for_new_day()
                    await self.notify_clients_of_day_change()

            logger.info("Completed integration of today's data from CurrentPoller")

        except Exception as e:
            logger.error(f"Error integrating today's data: {e}")
            return

    async def is_busy(self) -> bool:
        return not self._have_downloaded

    async def _shift_metadata_cache_for_new_day(self) -> None:
        """Shift the metadata cache when a new day rolls over."""
        await self._metadata_collector.shift_cache_for_new_day()

    async def get_metadata_for_date(
        self, location: Location, camera: Camera, date_str: str
    ) -> dict | None:
        """Get metadata for a specific date with caching.

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
            The metadata dictionary, or None if not found.
        """
        return await self._metadata_collector.get_metadata_for_date(
            location, camera, date_str
        )

    async def _metadata_exists_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> bool:
        """Check if metadata exists for a specific date."""
        date_str = day_obs.isoformat()
        return await self._metadata_collector.metadata_exists_for_date(
            location, camera, date_str
        )

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        await self._metadata_collector.stop_background_tasks()

    async def notify_clients_of_day_change(self) -> None:
        """Notify the clients that the day has changed."""
        for loc in self._locations:
            for cam in loc.cameras:
                if cam.online:
                    await notify_ws_clients(
                        Service.CALENDAR,
                        MessageType.DAY_CHANGE,
                        f"{loc.name}/{cam.name}",
                        "from historical",
                    )

    async def notify_update_all_calendars(self) -> None:
        """Notify all clients to update their calendars."""
        logger.info("Starting calendar update notifications")
        for loc in self._locations:
            for cam in loc.cameras:
                if cam.online:
                    loc_cam = (loc, cam)
                    calendar = self._calendar.get(loc_cam, {})
                    logger.info(
                        "Notifying calendar update for",
                        loc_cam=loc_cam,
                        calendar_size=len(calendar),
                    )
                    await notify_ws_clients(
                        Service.CALENDAR,
                        MessageType.CALENDAR_UPDATE,
                        f"{loc.name}/{cam.name}",
                        calendar,
                    )

    async def _initialise_location_store(self, location: Location) -> None:
        """Initialize location store using streamed object processing.

        This method processes objects page-by-page as they arrive from S3,
        enabling efficient ingestion of large object listings without
        buffering all results in memory.
        """
        for cam in location.cameras:
            if cam.online:
                prefixes = self._build_prefixes_for_camera(cam, self.prefix_extra)
                for prefix in prefixes:
                    try:
                        await self._process_objects_from_stream(location, prefix)
                    except Exception as e:
                        logger.error(
                            f"Error processing stream for prefix {prefix}: {e}"
                        )

    async def _get_objects_for_location(
        self, location: Location
    ) -> list[dict[str, str]]:
        """Downloads objects from the bucket for each online camera for the
        location.

        Returns
        -------
        objects :  `list` [`dict` [`str`, `str`]]
            A list of dicts representing bucket objects.
        """
        objects = []
        for cam in location.cameras:
            if cam.online:
                prefixes = self._build_prefixes_for_camera(cam, self.prefix_extra)

                for prefix in prefixes:
                    try:
                        objects.extend(
                            await self._get_objects_for_prefix(location, prefix)
                        )
                    except Exception as e:
                        logger.error(e)
        return objects

    async def _get_objects_for_prefix(
        self, location: Location, prefix: str
    ) -> list[dict[str, str]]:
        """Downloads objects from the bucket for the given prefix.

        Parameters
        ----------
        location : `Location`
            The location to get objects for.
        prefix : `str`
            The prefix to filter objects by.

        Returns
        -------
        objects :  `list` [`dict` [`str`, `str`]]
            A list of dicts representing bucket objects.
        """
        logger.info(
            "Fetching objects for prefix:",
            location=location.name,
            prefix=prefix,
        )
        client: S3Client = self._clients[location.name]
        objects = await client.async_list_objects(prefix=prefix)
        logger.info("Found:", num_objects=len(objects), prefix=prefix)
        return objects

    async def _process_objects_from_stream(
        self,
        location: Location,
        prefix: str,
        num_workers: int = 8,
    ) -> None:
        """Stream and process S3 objects as they arrive from pagination.

        This method uses a producer-consumer pattern with multiple workers to
        parallelize processing. Objects are fetched using date-based prefix
        parallelization to maximize S3 throughput.

        Parameters
        ----------
        location : `Location`
            The location to get objects for.
        prefix : `str`
            The prefix to filter objects by.
        num_workers : `int`, optional
            Number of concurrent worker tasks to process pages, by default 8.
        """
        logger.info(
            "Starting to process objects from stream",
            location=location.name,
            prefix=prefix,
        )

        # Queue for pages, with a reasonable buffer to allow prefetching
        page_queue: asyncio.Queue = asyncio.Queue(maxsize=20)

        async def fetch_pages_task() -> None:
            """Fetch pages from S3 and put them in the queue."""
            client: S3Client = self._clients[location.name]
            try:
                async for page_tuple in client.async_list_objects_by_date_parallel(
                    prefix=prefix,
                    start_date=self._start_date,
                    end_date=self._end_date,
                    num_workers=8,
                ):
                    await page_queue.put(page_tuple)
            finally:
                # Signal end of pages for all workers
                for _ in range(num_workers):
                    await page_queue.put(None)

        async def process_pages_task(worker_id: int) -> None:
            """Process pages from the queue."""
            while True:
                page_tuple = await page_queue.get()
                if page_tuple is None:
                    break

                _, page = page_tuple

                await self._ingest_objects(
                    location,
                    page,
                    replace_night_reports=True,
                    notify_structured_updates=False,
                )

        # Create fetch task and worker tasks
        fetch_task = asyncio.create_task(fetch_pages_task())
        worker_tasks = [
            asyncio.create_task(process_pages_task(i)) for i in range(num_workers)
        ]

        # Wait for all tasks to complete
        await asyncio.gather(fetch_task, *worker_tasks)

        logger.info(
            "Completed processing objects from stream",
            location=location.name,
            prefix=prefix,
        )

    async def store_events_structured(
        self, events: list[Event], location: Location
    ) -> None:
        """Store events by converting to dicts and using shared conversion."""
        # Convert Event objects to the expected dict format
        event_objects = [{"key": event.key} for event in events]
        structured_data, extension_info = await self._convert_objects_to_structured(
            event_objects, location
        )
        await self._merge_structured_data_into_cache(structured_data, extension_info)

    def get_extension_for_event(
        self,
        location: Location,
        camera: Camera,
        a_date: date,
        channel: Channel,
        seq_num: int | str,
    ) -> str:
        """Get the extension for a specific event, using default and
        exceptions pattern."""
        channel_date_key = (location, camera, a_date, channel)

        # Check if there's an exception for this seq_num
        if channel_date_key in self._extension_exceptions:
            exceptions = self._extension_exceptions[channel_date_key]
            if seq_num in exceptions:
                return exceptions[seq_num]

        # Return the default extension
        return self._channel_default_extensions.get(channel_date_key, "jpg")

    def reconstruct_filename(
        self,
        camera_name: str,
        channel_name: str,
        date_str: str,
        seq_num: int | str,
        ext: str,
    ) -> str:
        """Reconstruct filename from components."""
        if isinstance(seq_num, str):
            base_name = f"{camera_name}_{channel_name}_{date_str}_{seq_num}"
        else:
            base_name = f"{camera_name}_{channel_name}_{date_str}_{seq_num:06d}"
        return f"{base_name}.{ext}"

    async def get_structured_data_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, set[int | str]]:
        """Returns the structured data for a given date."""
        async with self._data_lock:
            if (
                (location, camera) not in self._structured_events
                or day_obs not in self._structured_events[(location, camera)]
            ):
                return {}

            with_channels = self._structured_events[(location, camera)][day_obs]
            return {
                channel.name: seq_nums for channel, seq_nums in with_channels.items()
            }

    async def get_all_extensions_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> TransmissableExtInfo:
        """Get all extensions (default and exceptions) for all channels on a
        given date.

        Structure of returned data:
        {channel_name: {"default": "ext", "exceptions": {seq_num: "ext", ...}}}
        """
        if (
            location,
            camera,
        ) not in self._structured_events or day_obs not in self._structured_events[
            (location, camera)
        ]:
            return {}

        extensions_info = {}
        for channel in self._structured_events[(location, camera)][day_obs]:
            default_ext = self._channel_default_extensions.get(
                (location, camera, day_obs, channel), "jpg"
            )
            exceptions = self._extension_exceptions.get(
                (location, camera, day_obs, channel), {}
            )
            extensions_info[channel.name] = {
                "default": default_ext,
                "exceptions": exceptions if exceptions else {},
            }
        return extensions_info

    async def get_events_for_date_structured(
        self, location: Location, camera: Camera, day_obs: date
    ) -> list[Event]:
        """Efficient event retrieval using optimized structure."""

        async with self._data_lock:
            if (
                (location, camera) not in self._structured_events
                or day_obs not in self._structured_events[(location, camera)]
            ):
                return []

            events = []
            for channel, seq_data in self._structured_events[(location, camera)][
                day_obs
            ].items():
                for seq_num in seq_data:
                    ext = self.get_extension_for_event(
                        location, camera, day_obs, channel, seq_num
                    )

                    # Reconstruct filename and key
                    filename = self.reconstruct_filename(
                        camera.name, channel.name, day_obs.isoformat(), seq_num, ext
                    )
                    if isinstance(seq_num, str):
                        # seq_num is 'final' or similar non-integer
                        key = f"{camera.name}/{day_obs.isoformat()}/{channel.name}/{seq_num}/{filename}"
                    else:
                        key = f"{camera.name}/{day_obs.isoformat()}/{channel.name}/{seq_num:06d}/{filename}"
                    logger.debug(
                        "Reconstructed key for event",
                        key=key,
                    )
                    events.append(Event(key=key))

            return events

    def add_to_calendar(
        self, location: Location, camera: Camera, day_obs: date, seq_num: int
    ) -> None:
        year, month, day = day_obs.year, day_obs.month, day_obs.day
        loc_cam = (location, camera)

        day_map = (
            self._calendar.setdefault(loc_cam, {})
            .setdefault(year, {})
            .setdefault(month, {})
        )
        day_map[day] = max(day_map.get(day, 0), seq_num)

    async def store_metadata_dates(
        self, location: Location, metadata_objs: list[dict[str, str]]
    ) -> None:
        for md_obj in metadata_objs:
            key = md_obj.get("key")
            hash = md_obj.get("hash")
            if not key or not hash:
                continue
            storage_name = location.name + "/" + key.split("/metadata")[0]
            _, cam_name, date_str = storage_name.split("/")
            self._metadata_collector.register_metadata_ref(
                f"{location.name}/{cam_name}", date_str, hash
            )
            camera: Camera | None = find_first(location.cameras, "name", cam_name)
            if camera is not None:
                a_date = date_str_to_date(date_str)
                self.add_to_calendar(location, camera, a_date, 0)

    async def get_night_report_payload(
        self, location: Location, camera: Camera, day_obs: date
    ) -> NightReport:
        """Returns a NightReport for the camera and date.

        Parameters
        ----------
        camera : `Camera`
            The given Camera.
        obs_date : `date`
            The given date.

        Returns
        -------
        report : `NightReport`
            A NightReport containing a list of Night Report Data and text
            metadata.
        """
        nr_data = await self._get_night_report_data(location, camera, day_obs)
        text_reports = [r for r in nr_data if r.group == "metadata"]
        report: NightReport = NightReport()
        if text_reports:
            text_report = text_reports[0]
            key = text_report.key
            client = self._clients[location.name]
            text_obj = await client.async_get_object(key)
            report.text = text_obj
            nr_data.remove(text_report)
        if nr_data:
            report.plots = nr_data
        return report

    async def _get_night_report_data(
        self, location: Location, camera: Camera, day_obs: date
    ) -> list[NightReportData]:
        date_str = day_obs.isoformat()
        report = []
        if location in self._nr_metadata:
            report = [
                nr
                for nr in self._nr_metadata[location]
                if nr.camera_name == camera.name and nr.day_obs == date_str
            ]
        return report

    async def night_report_exists_for(
        self, location: Location, camera: Camera, day_obs: date
    ) -> bool:
        nr_data = await self._get_night_report_data(location, camera, day_obs)
        if nr_data:
            return True
        else:
            return False

    async def get_events_for_date(
        self, location: Location, camera: Camera, a_date: date
    ) -> list[Event]:
        events_for_date = await self.get_events_for_date_structured(
            location, camera, a_date
        )
        return events_for_date

    async def get_channel_data_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[int, dict[str, dict]]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        channel_data = await make_table_from_event_list(events, camera.seq_channels())
        return channel_data

    async def get_per_day_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, dict[str, dict]]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        chan_names = [c.name for c in camera.pd_channels()]
        per_day_lists = [e for e in events if e.channel_name in chan_names]
        if not per_day_lists:
            return {}
        per_day = {}
        for event in per_day_lists:
            per_day[event.channel_name] = event.__dict__
        return per_day

    async def check_for_metadata_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> bool:
        date_str = day_obs.isoformat()
        return await self._metadata_collector.metadata_exists_for_date(
            location, camera, date_str
        )

    def flatten_calendar(self, location: Location, camera: Camera) -> dict[str, int]:
        """Flatten the calendar for a given location and camera.

        Returns a dict with keys as date strings and values as the number of
        events for that date.
        """
        calendar = self._calendar.get((location, camera), {})
        flat_calendar = {}
        for year in calendar:
            for month in calendar[year]:
                for day, seq_num in calendar[year][month].items():
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    flat_calendar[date_str] = seq_num
        return flat_calendar

    async def get_most_recent_day(
        self, location: Location, camera: Camera
    ) -> date | None:
        calendar = self._calendar.get((location, camera))
        if not calendar:
            return None
        year = max(calendar.keys())
        month = max(calendar[year].keys())
        day = max(calendar[year][month].keys())
        most_recent = date(year, month, day)
        if most_recent != get_current_day_obs():
            return most_recent
        # check there is more than one day in the calendar
        # if there is only one day, return None
        flat_calendar = self.flatten_calendar(location, camera)
        num_days = len(flat_calendar)
        if num_days <= 1:
            return None
        second_most_recent = sorted(flat_calendar.keys())[-2]
        return date_str_to_date(second_most_recent)

    async def get_most_recent_events(
        self, location: Location, camera: Camera
    ) -> list[Event]:
        day_obs = await self.get_most_recent_day(location, camera)
        if not day_obs:
            return []
        events_for_date = await self.get_events_for_date_structured(
            location, camera, day_obs
        )
        return events_for_date

    async def get_most_recent_event(
        self, location: Location, camera: Camera, channel: Channel
    ) -> Event | None:
        events = await self.get_most_recent_events(location, camera)
        events = [e for e in events if e.channel_name == channel.name]
        if not events:
            return None
        return max(events)

    def unarchive_events(self, archived_events: list[str]) -> list[Event]:
        return [Event(key=e) for e in archived_events]

    async def get_next_prev_event(
        self, location: Location, camera: Camera, event: Event
    ) -> tuple[dict | None, ...]:
        day_obs = event.day_obs_date()
        table = await self.get_channel_data_for_date(location, camera, day_obs)
        nxt_prv = await get_next_previous_from_table(table, event)
        return nxt_prv

    async def get_most_recent_channel_data(
        self, location: Location, camera: Camera
    ) -> dict[int, dict[str, dict]]:
        day = await self.get_most_recent_day(location, camera)
        if not day:
            return {}
        data = await self.get_channel_data_for_date(location, camera, day)
        return data

    async def get_camera_calendar(
        self, location: Location, camera: Camera
    ) -> dict[int, dict[int, dict[int, int]]]:
        """Returns a dict representing a calendar for the given Camera

        Provides a list of tuples for (days and max seq_num of Events), within
        a dict of months, within a dict keyed by year for the given Camera.

        Parameters
        ----------
        camera : `Camera`
            The given Camera object.

        Returns
        -------
        years : `dict` [`int`, `dict` [`int`, `dict` [`int`, `int` | `str`]]]
            A data structure for the view to iterate over with years, months,
            days and num. of events for that day for the given Camera.

        """
        return self._calendar.get((location, camera), {})

    async def get_all_channel_names_for_date_and_seq_num(
        self, location: Location, camera: Camera, day_obs: date, seq_num: int
    ) -> list[str]:
        """Returns a list of Events for the given date and seq_num.

        Parameters
        ----------
        camera : `Camera`
            The given Camera.
        day_obs : `date`
            The given date.
        seq_num : `int`
            The given sequence number.

        Returns
        -------
        chan_names : `list` [`str`]
            A list of channel names for the given date and seq_num.
        """
        loc_cam = (location, camera)
        if (
            loc_cam not in self._structured_events
            or day_obs not in self._structured_events[loc_cam]
        ):
            return []

        channels: list[Channel] = []
        for channel, seq_data in self._structured_events[loc_cam][day_obs].items():
            if seq_num in seq_data:
                channels.append(channel)

        return [channel.name for channel in channels]

    async def _make_structured_data_transmissable(
        self, structured_data: StructuredData, day: date
    ) -> TransmissableStructuredData:
        """Convert structured data for a given day into a format that can be
        transmitted over the websocket.

        Returns a dict where keys are channel names and values are lists of
        sequence numbers, compatible with frontend's
        createTableFromStructuredData.

        Parameters
        ----------
        structured_data : StructuredData
            The structured event data indexed by
            (location, camera, date, channel)
        day : date
            The specific date to extract data for

        Returns
        -------
        TransmissableStructuredData
            Dict with channel names as keys and seq_nums lists as values
        """
        transmissable: TransmissableStructuredData = {}
        for _, date_channel_data in structured_data.items():
            if day in date_channel_data:
                channels = date_channel_data[day]
                for channel, seq_nums in channels.items():
                    # Return seq_nums as a list (array), keyed by channel name
                    transmissable[channel.name] = list(seq_nums)
        return transmissable

    def _make_extension_info_transmissable(
        self,
        extension_info: ExtensionInfo,
        location: Location,
        camera: Camera,
        day: date,
    ) -> TransmissableExtInfo:
        """Convert extension info for a specific location, camera, and date
        into a format that can be transmitted over the websocket.

        Returns a dict where keys are channel names and values are dicts with
        'default' and 'exceptions' keys, compatible with frontend's
        createTableFromStructuredData.

        Parameters
        ----------
        extension_info : ExtensionInfo
            Extension info indexed by (location, camera, date, channel) tuples
        location : Location
            The location to extract extension info for
        camera : Camera
            The camera to extract extension info for
        day : date
            The date to extract extension info for

        Returns
        -------
        TransmissableExtInfo
            Dict with channel names as keys and ExtensionDict values
        """
        transmissable: TransmissableExtInfo = {}
        for (loc, cam, dt, channel), ext_dict in extension_info.items():
            if loc == location and cam == camera and dt == day:
                transmissable[channel.name] = ext_dict
        return transmissable
