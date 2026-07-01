#!/usr/bin/env python3
"""Estimate the resident in-memory cost of RubinTV's metadata cache.

The metadata cache (``MetadataCollector._metadata_cache``) stores, per
``location/camera``, up to ``METADATA_CACHE_DAYS`` parsed ``metadata.json``
dicts -- i.e. exactly ``json.loads(body)`` for each day's file. This script
samples a *small* number of the most recent days per camera, measures the real
on-disk (S3) byte size and the real deep in-memory size of the parsed dict,
then extrapolates to a full cache at a chosen cap.

It is deliberately lightweight so it can be run against USDF without hogging
resources:
  * only ``--sample-days`` files per camera are downloaded (default 5),
  * downloads are strictly serial (one object at a time, one connection),
  * a small sleep between fetches keeps S3 pressure low,
  * nothing is held resident -- each sample is measured then discarded.

The extrapolation reports the projected cache size for the CURRENT cap (60) and
for a proposed smaller cap, so the effect of lowering the cap is explicit.

Usage (at USDF)::

    python estimate_metadata_memory.py \
        --profile <aws_profile> \
        --endpoint-url https://s3.....slac.stanford.edu \
        --bucket rubintv \
        --location usdf \
        --cameras lsstcam lsstcam_aos \
        --sample-days 5 \
        --current-cap 60 \
        --proposed-cap 5

If ``--cameras`` is omitted the script lists the camera prefixes under the
location and samples each. Use ``--max-cameras`` to bound that.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from time import monotonic, sleep
from typing import Any

import boto3
from botocore.config import Config as BotoConfig


# ---------------------------------------------------------------------------
# Deep sizing -- mirror how the parsed dict actually sits in memory.
# ---------------------------------------------------------------------------
def deep_sizeof(obj: object, _seen: set[int] | None = None) -> int:
    """Recursively measure the in-memory footprint of a Python object.

    Follows dict/list/tuple/set containers and their contents, de-duplicating
    by id() so shared/interned objects are only counted once -- the same way
    they occupy memory once in the live cache.
    """
    if _seen is None:
        _seen = set()
    oid = id(obj)
    if oid in _seen:
        return 0
    _seen.add(oid)
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            size += deep_sizeof(k, _seen)
            size += deep_sizeof(v, _seen)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for item in obj:
            size += deep_sizeof(item, _seen)
    return size


@dataclass
class DaySample:
    date_str: str
    raw_bytes: int
    parsed_bytes: int


@dataclass
class CameraResult:
    loc_cam: str
    samples: list[DaySample] = field(default_factory=list)
    available_days: int = 0  # how many metadata.json files exist for this cam

    @property
    def n(self) -> int:
        return len(self.samples)

    @property
    def mean_parsed(self) -> float:
        return sum(s.parsed_bytes for s in self.samples) / self.n if self.n else 0.0

    @property
    def mean_raw(self) -> float:
        return sum(s.raw_bytes for s in self.samples) / self.n if self.n else 0.0

    @property
    def parse_ratio(self) -> float:
        """Parsed-dict bytes / raw-json bytes -- the json.loads() blow-up."""
        return self.mean_parsed / self.mean_raw if self.mean_raw else 0.0


# ---------------------------------------------------------------------------
# S3 helpers -- intentionally minimal and serial.
# ---------------------------------------------------------------------------
def make_client(profile: str | None, endpoint_url: str | None) -> Any:
    cfg = BotoConfig(
        retries={"max_attempts": 5, "mode": "standard"},
        max_pool_connections=1,  # keep it gentle
    )
    session = boto3.Session(
        region_name="us-east-1",
        profile_name=profile if profile else None,
    )
    return session.client("s3", endpoint_url=endpoint_url, config=cfg)


def list_cameras(
    client: Any, bucket: str, location: str, max_cameras: int
) -> list[str]:
    """List camera prefixes directly under the bucket (delimiter-based)."""
    cams: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix="", Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            name = cp["Prefix"].rstrip("/")
            cams.append(name)
    if max_cameras:
        cams = cams[:max_cameras]
    return cams


def find_recent_metadata_dates(
    client: Any, bucket: str, camera: str, sample_days: int, lookback_days: int
) -> tuple[list[str], int]:
    """Find the most recent dates that have a metadata.json for this camera.

    Walks backwards from today HEAD-checking ``camera/<date>/metadata.json``.
    Returns (dates_to_sample, approx_available_count). ``lookback_days`` bounds
    the search so a camera with no data doesn't scan forever.
    """
    today = date.today()
    found: list[str] = []
    checked = 0
    available_estimate = 0
    d = today
    while checked < lookback_days and len(found) < sample_days:
        date_str = d.isoformat()
        key = f"{camera}/{date_str}/metadata.json"
        try:
            client.head_object(Bucket=bucket, Key=key)
            found.append(date_str)
            available_estimate += 1
        except client.exceptions.ClientError:
            pass
        checked += 1
        d = d - timedelta(days=1)
    return found, available_estimate


def sample_camera(
    client: Any,
    bucket: str,
    camera: str,
    sample_days: int,
    lookback_days: int,
    sleep_between: float,
) -> CameraResult:
    result = CameraResult(loc_cam=camera)
    dates, _ = find_recent_metadata_dates(
        client, bucket, camera, sample_days, lookback_days
    )
    result.available_days = len(dates)  # lower bound; refined below if needed
    for date_str in dates:
        key = f"{camera}/{date_str}/metadata.json"
        try:
            obj = client.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
            raw = len(body)
            parsed = json.loads(body)  # exactly what the cache stores
            result.samples.append(
                DaySample(
                    date_str=date_str,
                    raw_bytes=raw,
                    parsed_bytes=deep_sizeof(parsed),
                )
            )
            del parsed, body  # do not retain -- keep footprint tiny
        except Exception as e:  # noqa: BLE001 -- report and continue
            print(f"    ! skip {key}: {e}", file=sys.stderr)
        if sleep_between:
            sleep(sleep_between)
    return result


# ---------------------------------------------------------------------------
# Reporting / extrapolation.
# ---------------------------------------------------------------------------
def human(nbytes: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:,.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:,.1f} TiB"


def report(results: list[CameraResult], current_cap: int, proposed_cap: int) -> None:
    results = [r for r in results if r.n]
    if not results:
        print("No samples collected -- nothing to extrapolate.")
        return

    print()
    print("=" * 78)
    print("PER-CAMERA SAMPLES (most-recent days)")
    print("=" * 78)
    print(
        f"{'camera':<22} {'n':>3} {'raw~':>10} {'parsed~':>10} "
        f"{'blowup':>7} {'/day cache':>12}"
    )
    for r in sorted(results, key=lambda x: -x.mean_parsed):
        print(
            f"{r.loc_cam:<22} {r.n:>3} {human(r.mean_raw):>10} "
            f"{human(r.mean_parsed):>10} {r.parse_ratio:>6.1f}x "
            f"{human(r.mean_parsed):>12}"
        )

    # Recent-days sampling is a WORST-CASE proxy for the whole cache: the
    # newest nights are the busiest, so extrapolating the recent mean across
    # the full cap over-estimates slightly -- the safe direction for a limit.
    def cache_total(cap: int) -> float:
        return sum(r.mean_parsed * cap for r in results)

    total_current = cache_total(current_cap)
    total_proposed = cache_total(proposed_cap)

    print()
    print("=" * 78)
    print("EXTRAPOLATED RESIDENT CACHE COST")
    print("=" * 78)
    print(f"cameras sampled:        {len(results)}")
    print(
        f"mean parsed dict / day: {human(sum(r.mean_parsed for r in results)/len(results))}"
    )
    print(
        f"mean json.loads blowup: {sum(r.parse_ratio for r in results)/len(results):.1f}x raw bytes"
    )
    print()
    print(f"  cap = {current_cap:>3} days/cam  ->  {human(total_current)}   (current)")
    print(
        f"  cap = {proposed_cap:>3} days/cam  ->  {human(total_proposed)}   (proposed)"
    )
    print()
    if total_current:
        pct = 100.0 * (total_current - total_proposed) / total_current
        print(
            f"  reduction: {human(total_current - total_proposed)} freed "
            f"({pct:.0f}% smaller), factor {current_cap/proposed_cap:.0f}x"
        )
    print()
    print(
        "Note: this is the RESIDENT cache only. Peak is higher: json.loads()\n"
        "transiently allocates the parsed graph on top of the cached dict\n"
        "during each (pre)fetch. Lowering the cap shrinks the resident floor\n"
        "the transient spikes sit on, AND reduces how many parses happen on a\n"
        "prefetch/recheck sweep."
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", default=None, help="AWS profile name")
    p.add_argument("--endpoint-url", default=None, help="S3 endpoint URL")
    p.add_argument("--bucket", required=True, help="Bucket name")
    p.add_argument("--location", default="", help="Location label (for output only)")
    p.add_argument(
        "--cameras",
        nargs="*",
        default=None,
        help="Camera prefixes to sample. If omitted, discovered from bucket.",
    )
    p.add_argument("--max-cameras", type=int, default=8)
    p.add_argument("--sample-days", type=int, default=5)
    p.add_argument(
        "--lookback-days",
        type=int,
        default=120,
        help="How far back to search for the sample-days most recent files.",
    )
    p.add_argument("--current-cap", type=int, default=60)
    p.add_argument("--proposed-cap", type=int, default=5)
    p.add_argument(
        "--sleep-between",
        type=float,
        default=0.2,
        help="Seconds to sleep between object fetches (be gentle on S3).",
    )
    args = p.parse_args()

    client = make_client(args.profile, args.endpoint_url)

    cameras = args.cameras
    if not cameras:
        print("Discovering cameras...", file=sys.stderr)
        cameras = list_cameras(client, args.bucket, args.location, args.max_cameras)
    print(f"Sampling {len(cameras)} camera(s): {', '.join(cameras)}", file=sys.stderr)

    t0 = monotonic()
    results: list[CameraResult] = []
    for cam in cameras:
        print(f"  sampling {cam} ...", file=sys.stderr)
        r = sample_camera(
            client,
            args.bucket,
            cam,
            args.sample_days,
            args.lookback_days,
            args.sleep_between,
        )
        results.append(r)

    report(results, args.current_cap, args.proposed_cap)
    print(f"\n(sampled in {monotonic() - t0:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
