# RubinTV: System Overview & Rebuild Plan

## Table of Contents

1. [What RubinTV Does](#1-what-rubintv-does)
2. [Current Architecture](#2-current-architecture)
3. [Data Model & S3 Bucket Structure](#3-data-model--s3-bucket-structure)
4. [Background Workers](#4-background-workers)
5. [Real-Time Data Flow](#5-real-time-data-flow)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Pain Points & Motivations for Rebuild](#7-pain-points--motivations-for-rebuild)
8. [Rebuild Plan](#8-rebuild-plan)

---

## 1. What RubinTV Does

RubinTV is a web application for the Vera C. Rubin Observatory that provides
**near-real-time and historical viewing of telescope data products** -
plots, images, mosaics, movies, and metadata - produced by various cameras
and instruments across multiple processing sites.

### Core User Stories

- **Observers on the summit** watch the current night's data as images arrive
  from LSSTCam, AuxTel, AllSky, TMA, etc. They see per-sequence-number plots
  (e.g. witness detector images, PSF analysis, mount torques) and per-day
  artifacts (e.g. whole-night movies).

- **Operators** view night reports (text + plots summarizing a night's
  evolution) and monitor detector cluster worker status (busy/free/missing).

- **Engineers** use the admin panel to control pipeline parameters via Redis
  (AOS pipeline selection, chip selection strategy) and view readback of those
  controls.

- **Anyone** browses historical data by date (calendar picker), views metadata
  tables (exposure time, image type, airmass, etc.), and navigates between
  sequence numbers.

### Deployment Sites

The app runs in multiple contexts with different S3 bucket configurations:

| Site                            | Description                    | Bucket Source               |
| ------------------------------- | ------------------------------ | --------------------------- |
| **summit**                      | On the mountain, direct S3     | `rubintv` bucket            |
| **base** / **tucson**           | Teststands (BTS/TTS)           | `rubintv` bucket            |
| **usdf**                        | USDF at SLAC, main production  | `rubin-rubintv-data-usdf`   |
| **summit-usdf**                 | Summit data replicated to SLAC | `rubin-rubintv-data-summit` |
| **base-usdf** / **tucson-usdf** | Teststand data at SLAC         | Respective buckets          |
| **local** / **gha**             | Development / CI               | Configurable                |

Each deployment sees only the locations relevant to its site, controlled by
`bucket_configurations` in `models_data.yaml`.

---

## 2. Current Architecture

### Tech Stack

| Layer            | Technology                                                               |
| ---------------- | ------------------------------------------------------------------------ |
| Web framework    | FastAPI (Python 3.12+)                                                   |
| Background tasks | `asyncio.create_task()` in the app lifespan                              |
| Data storage     | S3 (boto3) - the app is read-only; data is written by external pipelines |
| Real-time        | WebSocket (FastAPI) + Redis pub/sub & streams                            |
| Cache            | In-memory Python dicts + gzipped pickle persistence to disk              |
| Templating       | Jinja2 (server-rendered shell)                                           |
| Frontend         | React 19 + TypeScript (Webpack bundles mounted into Jinja templates)     |
| Metadata cache   | LRU OrderedDict with per-key async locks                                 |
| Serialization    | orjson + gzip for WebSocket and API responses                            |
| Deployment       | Docker image on Kubernetes, served behind a reverse proxy                |

### Application Startup Sequence

```
create_app()
  |
  lifespan():
    1. ModelsInitiator()         -- load YAML config
    2. HistoricalPoller(locs)    -- create historical cache manager
    3. Redis connect             -- if available
    4. DetectorStatusHandler()   -- Redis stream reader for cluster status
    5. RedisSubscriber()         -- keyspace event subscriber for control readback
    6. S3 client pool            -- one shared client per location
    7. CurrentPoller.start()     -- begin ~1s polling loop
    8. HistoricalPoller.run()    -- begin 12h/2m background scan
    9. Mount DDV, exp_checker, static assets
```

### Route Map

All external routes are prefixed with `/rubintv` (configurable).

**Pages (HTML)**:

- `/` - Home: list of locations
- `/{location}` - Location page: camera grid
- `/{location}/{camera}` - Camera table view (per-seq-num data table)
- `/{location}/{camera}/{channel}` - Single channel view (latest image)
- `/{location}/{camera}/mosaic` - Mosaic/movies view
- `/{location}/{camera}/night_report` - Night report viewer
- `/{location}/{camera}/night_report/{date}` - Historical night report
- `/{location}/{camera}/allsky` - All-sky camera viewer
- `/{location}/{camera}/detectors` - Detector cluster status
- `/{location}/{camera}/admin` - Admin control panel

**API** (`/rubintv/api`):

- `GET /` - List all locations
- `GET /{location}` - Location details
- `GET /{location}/{camera}` - Camera details
- `GET /{location}/{camera}/date/{date}` - All events for a date
- `GET /{location}/{camera}/{channel}/current` - Most recent event
- `GET /{location}/{camera}/event?key=...` - Specific event by S3 key
- `GET /{location}/{camera}/night_report` - Current night report
- `GET /{location}/{camera}/night_report/{date}` - Historical night report
- `GET /{location}/{camera}/metadata/{date}` - Metadata for a date
- `GET /redis/controlvalues` - Current Redis control readback values
- `POST /redis` - Set a Redis control value
- `POST /historical_reset` - Force full historical rescan

**WebSockets**:

- `/rubintv/ws/data` - Live data updates (camera tables, channel events, night reports, calendar, detectors, admin)
- `/rubintv/ws/heartbeats` - Service health monitoring
- `/rubintv/ws/ddv` - DDV Flutter app communication
- `/ws` - Internal DDV worker communication

**Proxies**:

- `/{location}/{camera}/{channel}/{date}/{seq}/{filename}` - Proxied S3 object fetch (images/videos)

---

## 3. Data Model & S3 Bucket Structure

### S3 Object Key Patterns

All data in S3 follows strict naming conventions. The app **never writes** to
S3 - it only reads objects deposited by external processing pipelines.

#### Channel Events (images, plots, movies)

```
{camera}/{day_obs}/{channel}/{seq_num:06d}/{filename}.{ext}

Examples:
  lsstcam/2026-04-10/witness_detector/000001/image.png
  lsstcam/2026-04-10/focal_plane_mosaic/000042/mosaic.jpg
  auxtel/2026-04-10/monitor/000003/monitor.png
  auxtel/2026-04-10/movies/final/movie.mp4        (per-day: seq_num="final")
  lsstcam/2026-04-10/day_movie/final/movie.mp4
```

Each event is parsed via regex into: `camera_name`, `day_obs`, `channel_name`,
`seq_num` (int or "final"), `filename`, `ext`.

#### Metadata

```
{camera}/{day_obs}/metadata.json

Content: JSON dict keyed by seq_num (as string), each value is a dict of
metadata column -> value. Example:
{
  "1": { "Exposure time": 30.0, "Image type": "science", "Airmass": 1.2, ... },
  "2": { "Exposure time": 15.0, "Image type": "flat", ... }
}
```

A metadata hash (ETag) is used to detect changes without re-downloading.

#### Night Reports

```
Plots:    {camera}/{day_obs}/night_report/{group}/{filename}.{ext}
Metadata: {camera}/{day_obs}/night_report/{filename}_md.json

The _md.json contains structured text items for the night report:
[
  { "type": "multiline", "key": "summary", "title": "Summary", "content": "..." },
  { "type": "keyvalues", "key": "stats", "title": "Statistics", "content": [...] }
]
```

### Core Data Types

**Event** - A single data product in a channel:

```
key, camera_name, day_obs, channel_name, seq_num, filename, ext
```

**StructuredData** - Compressed index: `{channel_name: set[seq_num]}`

- This is the primary way the frontend knows what data exists

**ExtensionInfo** - File extension mapping:

```
{channel_name: {default: "png", exceptions: {42: "jpg", "final": "mp4"}}}
```

- Allows the frontend to construct S3 keys without querying for each one

**ChannelData** - Full table: `{seq_num: {channel_name: event_dict}}`

**CameraPageData** - Aggregated page payload:

```
nr_exists, per_day, structured_data, extension_info, metadata
```

### Configuration Model Hierarchy

```
models_data.yaml
  |
  +-- bucket_configurations    (site -> [location_names])
  +-- locations[]              (name, bucket, profile, endpoint, camera_groups)
  +-- cameras[]                (name, channels[], metadata_columns, etc.)
  +-- services                 (heartbeat service definitions)
  +-- metadata_columns         (per-camera column name -> description)
  +-- admin_for                (per-location admin user lists)
  +-- redis_detectors          (Redis stream key -> display name)
  +-- admin_redis_menus        (control menu definitions)
```

A `Location` has `camera_groups: dict[str, list[str]]` - group label to camera
name list. The `ModelsInitiator` resolves camera names to `Camera` objects and
attaches them to each location.

### Cameras and Channels

The system currently defines ~20 cameras with ~60 channels total. Key cameras:

| Camera                | Channels                                                                                                                                                          | Notes                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **lsstcam**           | witness_detector, focal_plane_mosaic, calexp_mosaic, psf_shape_azel, fwhm_focal_plane, mount, imexam, event_timeline, day_movie (per-day)                         | Main science camera, has image_viewer_link, mosaic view |
| **lsstcam_aos**       | fp_pairing_plot, fp_donut_gallery, zk_residual_pyramid, zk_measurement_pyramid, focus_sweep, psf_zk_panel, donut_fits, zernike_predicted_fwhm, dof_predicted_fwhm | Active optics system                                    |
| **lsstcam_guider**    | full_movie, star_movie, centroid_alt_az, flux_trend, psf_trend                                                                                                    | Guider camera                                           |
| **auxtel**            | monitor, imexam, specexam, mount, movies (per-day)                                                                                                                | Auxiliary telescope                                     |
| **tma**               | mount, m1m3_hardpoint                                                                                                                                             | Telescope mount assembly                                |
| **allsky**            | movies (per-day), stills (per-day)                                                                                                                                | All-sky camera                                          |
| **comcam**            | (similar to lsstcam)                                                                                                                                              | Commissioning camera (legacy)                           |
| **startracker\_\*\*** | raw, analysis                                                                                                                                                     | Three variants: narrow, wide, fast                      |

Channel properties:

- `per_day: bool` - If true, this channel has one artifact per day (e.g. a movie), not per-seq-num
- `colour` - CSS colour for UI display
- `icon` - Optional icon name
- `label` - Short display label (defaults to title)

### Day Observation Boundary

The observatory uses **UTC-12** as the date rollover. This means the "observing
day" (day_obs) runs from noon UTC to noon UTC the next day. The function
`get_current_day_obs()` implements this.

---

## 4. Background Workers

### CurrentPoller

**Purpose**: Polls S3 every ~1 second for today's data and pushes updates to
WebSocket clients.

**Loop** (`poll_buckets_for_todays_data`):

```
every ~1s:
  for each location:
    for each camera:
      list S3 objects under "{camera}/{today}"
      sieve out metadata.json -> process_metadata_file()
      sieve out night_report/ objects -> process_night_report_objects()
      remaining = channel events -> process_channel_objects()
    poll for yesterday's missing per-day data
```

**State held in memory** (keyed by `"{location}/{camera}"`):

- `_objects` - raw S3 object listings
- `_events` - parsed Event objects
- `_metadata` - metadata.json contents
- `_table` - channel table (seq_num -> channel -> event_dict)
- `_structured_events` - compressed index
- `_extension_info` - file extension mapping
- `_per_day` - per-day channel data
- `_most_recent_events` - latest event per channel
- `_nr_metadata` / `_night_reports` - night report state

**Day rollover**: When `get_current_day_obs()` changes:

1. Integrates today's data into HistoricalPoller
2. Records missing per-day channel prefixes (to keep polling yesterday)
3. Clears all state

### HistoricalPoller

**Purpose**: Caches historical S3 data (all dates before today) and serves
historical queries.

**Polling schedule**:

- Full scan of all buckets: every **12 hours** (or on first startup)
- Yesterday's data: every **2 minutes**
- Cache persistence: gzipped pickle at `./historical_cache.pkl.gz` or `/scratch/`

**Data structures** (keyed by `(Location, Camera)` tuple):

- `_structured_events` - `{date: {channel: set[seq_nums]}}`
- `_channel_default_extensions` - `{date: {channel: default_ext}}`
- `_extension_exceptions` - `{date: {channel: {seq_num: ext}}}`
- `_nr_metadata` - `{date: [NightReportData]}`
- `_calendar` - date lists for the calendar picker
- `_metadata_collector` - MetadataCollector instance

**Key behaviors**:

- Parallel S3 listing with configurable thread pool (8-12 workers)
- Lists in reverse-chronological order (recent dates first)
- Can filter by start/end date
- `integrate_todays_data()` - called by CurrentPoller on day rollover

### MetadataCollector

**Purpose**: LRU cache for metadata.json files from S3.

- Max 60 days cached per location/camera
- Per-key async locks prevent duplicate S3 fetches
- Background prefetching (pauses during active user requests)
- Tracks metadata ref hashes to detect changes

### DetectorStatusHandler

**Purpose**: Reads Redis streams for detector cluster worker status.

- Listens to streams like `CLUSTER_STATUS_SFM_SET_0`, `CLUSTER_STATUS_AOS_SET_0`, etc.
- Worker statuses: free, busy, missing, queued, restarting, guest
- Pushes status updates to WebSocket clients subscribed to the `detectors` service

### RedisSubscriber

**Purpose**: Monitors Redis keyspace events for control readback changes.

- Subscribes to keyspace notifications for keys ending in `_READBACK`
- When a value changes, pushes the new value to admin WebSocket clients

---

## 5. Real-Time Data Flow

### WebSocket Protocol

**Connection flow**:

1. Client connects to `/rubintv/ws/data`
2. Server sends `clientID: {uuid}`
3. Client sends subscription messages:
   ```json
   {"clientID": "uuid", "message": "camera summit-usdf/lsstcam"}
   {"clientID": "uuid", "message": "channel summit-usdf/lsstcam/witness_detector"}
   {"clientID": "uuid", "message": "nightreport summit-usdf/lsstcam"}
   ```
4. Server validates and registers subscriptions
5. Server sends current state for the subscribed service
6. Ongoing: server pushes updates as data changes

**Message format** (server -> client):

```json
{
  "dataType": "event",        // ServiceMessageTypes value
  "payload": { ... }          // Event dict, structured data, metadata, etc.
}
```

**Service types and their message types**:

| Service            | Messages Sent                                                                   |
| ------------------ | ------------------------------------------------------------------------------- |
| `camera`           | channelData (structuredData + extensionInfo), metadata, perDay, nightReportLink |
| `channel`          | event, prevNext, allChannels, latestMetadata                                    |
| `nightreport`      | nightReport                                                                     |
| `calendar`         | latestMetadata, dayChange, perDay                                               |
| `historicalStatus` | historicalStatus (busy/idle)                                                    |
| `detectors`        | detectorStatus                                                                  |
| `admin`            | controlReadback                                                                 |

### Data Push Path

```
S3 (external pipelines write objects)
  |
  v
CurrentPoller (polls S3 every ~1s)
  |
  +-- Detects new/changed objects
  |     |
  |     v
  +-- Parses into Events
  |     |
  |     +-> notify_ws_clients(CAMERA, channelData, ...)
  |     +-> notify_ws_clients(CHANNEL, event, ...)
  |     +-> notify_ws_clients(CAMERA, metadata, ...)
  |     +-> notify_ws_clients(NIGHTREPORT, nightReport, ...)
  |
  v
WebSocket Handler
  |
  +-- Looks up subscribed clients for the service/location/camera
  +-- Serializes with orjson + gzip
  +-- Sends to each connected client
```

### Redis Integration

```
External pipeline  -->  Redis SET key  -->  Redis keyspace notification
                                                    |
                                                    v
                                            RedisSubscriber
                                                    |
                                                    v
                                            notify_ws_clients(ADMIN, controlReadback)

External pipeline  -->  Redis XADD stream  -->  DetectorStatusHandler
                                                        |
                                                        v
                                                notify_ws_clients(DETECTORS, detectorStatus)
```

---

## 6. Frontend Architecture

### Rendering Model

The app uses a **hybrid server/client rendering** approach:

1. **Server**: Jinja2 renders the HTML shell with an `APP_DATA` JavaScript
   object embedded in a `<script>` tag. This contains camera config, location
   data, initial calendar data, channel definitions, etc.

2. **Client**: React mounts into `<div id="root">` and reads `APP_DATA` from
   `window`. The WebSocket client connects and begins receiving live updates.

### Webpack Entry Points

Each page has its own Webpack bundle:

| Bundle         | Page              | Key Components                                      |
| -------------- | ----------------- | --------------------------------------------------- |
| `camera-table` | Camera table view | CameraTable, TableView, TableControls, MediaDisplay |
| `detectors`    | Detector status   | Detector cards                                      |
| `allsky`       | All-sky viewer    | AllSky image display                                |
| `admin`        | Admin panel       | AdminPanels with Redis controls                     |
| `night-report` | Night report      | NightReport, plot galleries                         |

### WebSocket Client (`ws-service-client.ts`)

- Uses `reconnecting-websocket` for auto-reconnection
- Manages subscriptions by service type
- Routes incoming messages to registered listeners
- Dispatches custom DOM events for cross-component communication

### State Management

- React Context for shared state (camera data, WebSocket connection status)
- LocalStorage for user column preferences (which metadata columns to show)
- URL-based state for date, camera, location (standard routing)

---

## 7. Pain Points & Motivations for Rebuild

> **Note**: This section should be filled in with your specific motivations.
> Common issues in the current architecture include:

### Architecture

- All background state is held in Python dicts in the web server process
- No horizontal scaling: single process holds all cache state
- Historical cache is a gzipped pickle blob - brittle, opaque, hard to debug
- Tight coupling between polling, caching, and notification logic
- S3 listing is expensive and done repeatedly (full prefix listing every 12h)

### Frontend

- Hybrid Jinja2 + React creates awkward boundaries
- Server-rendered initial state (`APP_DATA`) duplicates what the API provides
- Multiple Webpack entry points = slow builds, hard to share state across pages
- No client-side routing (full page reload between views)

### WebSocket Protocol

- Custom text-based subscription protocol
- No authentication or authorization on WebSocket connections
- Client must subscribe per-service; no batch subscription
- Message types are stringly typed

### Data Flow

- CurrentPoller polls S3 every ~1s per camera per location - doesn't scale
- HistoricalPoller does full bucket scans every 12h
- No incremental S3 change detection (no S3 event notifications)
- Day rollover logic is complex and fragile

### Operational

- No database - all state is in-memory or pickled to disk
- Redis is optional but features silently degrade without it
- Admin auth is username-list based in YAML
- No metrics, alerting, or observability beyond structlog

---

## 8. Rebuild Plan

### Phase 0: Key Decisions (Resolved)

These decisions are based on the constraints of the deployment environment
and shape the entire rebuild.

#### Decision 1: S3 Ingestion Strategy

**Status**: Polling first, behind an abstraction, with a Kafka-backed
event source as the planned next source (not the initial build).

The S3 buckets are Ceph-based. Notification sinks are no longer purely
hypothetical: **summit now has a Kafka topic** fed by a Ceph bucket
notification, and **USDF is expected to get one soon**. Availability still
differs per site, so polling remains the baseline that works everywhere.

The architecture should:

- Start with polling (proven, works everywhere, no per-site dependency)
- Abstract the ingestion behind a `DataSource` interface so a Kafka
  consumer can be swapped in per-site without touching downstream logic
- Design the internal event flow as push-based (the source pushes into an
  event bus), so moving from "poll then push" to "notification then push"
  only changes the source

The summit notification is configured as a `CephBucketNotification`:

```yaml
apiVersion: ceph.rook.io/v1
kind: CephBucketNotification
metadata:
  name: lsst.s3.rubin.tv
  namespace: rook-ceph
spec:
  topic: lsst.s3.rubin.tv
  events:
    - s3:ObjectCreated:*
    - s3:ObjectRemoved:*
```

Note `s3:ObjectRemoved:*` is emitted too - the event source must handle
object removal, not just creation (historical data is mutable; fields and
objects can disappear). The `DataSource` interface should therefore expose
both "object created" and "object removed" semantics regardless of whether
the concrete source derives them from a diff (polling) or receives them
directly (Kafka).

#### Decision 2: Storage - In-Memory with File Cache

**Status**: In-memory primary, flat file backup. No database.

Constraints:

- PVC scratch space is available at most (not all) pod locations
- A PVC failure must not take down the app
- Single replica, no need for shared state

Architecture:

- **Primary store**: In-memory data structures (same as today, but cleaner)
- **Cache file**: Serialized to disk when PVC is available, for faster
  restarts. If the file is missing or corrupt, the app rebuilds from S3.
- **SQLite consideration**: SQLite on PVC _could_ replace the pickle cache
  with something queryable and incrementally writable. The benefit over a
  flat file is that you can write individual days without reserializing
  the entire cache. The risk (PVC failure) is mitigated by treating it as
  a warm-start optimisation, not a requirement. The app always falls back
  to a full S3 scan. **Recommendation**: Start with a cleaner flat-file
  format (e.g. one JSON file per location/camera/date, or a single
  structured JSON index). Evaluate SQLite later if the file-per-day
  approach becomes unwieldy with ~5000 objects/day across many cameras.

#### Decision 3: No Horizontal Scaling

Single replica. This simplifies everything - in-memory state is fine,
no distributed coordination needed.

#### Decision 4: Frontend - React SPA

**Status**: Full SPA with React, client-side routing, and client-side
data caching.

**On your question about client-side caching**: Yes - modern React data
fetching libraries provide sophisticated client-side caching _without_
any server involvement. This is one of the biggest wins of the rebuild.
Here's how the landscape breaks down:

| Approach                         | What it does                                                                                                             | Best for                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **React Query (TanStack Query)** | Caches API responses in browser memory. Automatic refetching, stale-while-revalidate, background refresh, deduplication. | REST API data: historical dates, metadata, night reports, calendar |
| **WebSocket state**              | Live data pushed by server, held in React state/context                                                                  | Today's data: current events, structured data, detector status     |
| **Browser Cache-Control**        | HTTP cache headers on proxied S3 images                                                                                  | Images/videos: once an image for seq 42 exists, it never changes   |

**Concrete example of how this changes the UX**:

Today: User views lsstcam on 2026-03-15, navigates away, comes back
-> full API call, loading spinner, wait for response.

With React Query: User views lsstcam on 2026-03-15, navigates away,
comes back -> cached data renders instantly, background refetch happens
silently. If nothing changed, no visual update. If new data arrived,
it merges in seamlessly.

**Recommended stack**:

- **Vite** for build tooling (10-50x faster than Webpack in dev)
- **React Router** for client-side routing (keeps it simple, no SSR
  framework overhead - this is an embargoed internal app, SEO is
  irrelevant)
- **TanStack Query** for server state / API caching
- **A WebSocket hook** (custom or `use-websocket`) for live data

This avoids Next.js/Remix entirely. Those frameworks add SSR, server
components, and deployment complexity that you don't need. A plain React
SPA served as static files from FastAPI is simpler and maps directly to
the current architecture. The backend remains a pure API server.

#### Decision 5: Auth - Username List (Unchanged)

The app is embargoed and not publicly reachable. Current username-list
model in YAML is sufficient.

#### Decision 6: Scope - DDV and exp_checker Included

Both sub-apps are in scope. They can be mounted as sub-paths of the
main app, same as today.

#### Decision 7 - Multi-Tab / Multi-Window

**Status**: Each browser tab is an independent, self-booting instance of
the SPA. Live data is coordinated by **one WebSocket per tab** (no shared
worker, no cross-tab state sync).

**The requirement**: Observers need several tabs (or windows, across
multiple monitors) open at once, each showing a *different* view that
*updates live and independently* - e.g. the lsstcam table in one tab, a
witness-detector channel in another, detector status in a third.

**Why an SPA handles this cleanly**: Browser tabs do not share a
JavaScript runtime - each tab loads and runs the app independently. So the
SPA-vs-MPA distinction is not the relevant axis. What matters is that
**each tab's URL fully describes its view**, so a tab can boot itself into
that exact state with no dependency on any other tab. Opening a second tab
at `/summit/lsstcam/witness_detector` simply starts a second, independent
copy of the SPA that routes to that view, opens its own WebSocket, and
subscribes to its own data.

**What this forbids** (and why the old `APP_DATA`-injected-once model could
not do this safely): no reliance on in-memory singleton state that only
exists in the first-loaded tab. In the rebuild, every tab fetches its own
config from the API and opens its own connection. There is no shared
client-side source of truth between tabs.

**Constraints this imposes on the design**:

- **Path-based routing** (not hash routing): the URL is the complete,
  reloadable, bookmarkable description of a tab's state. FastAPI serves a
  catch-all route returning `index.html` so deep links survive a hard
  reload. (This supersedes any earlier ambiguity about routing style.)
- **One WebSocket per tab**: each tab subscribes only to what it is
  currently viewing. N tabs = N connections. The summit user count is
  small, so this is acceptable; a SharedWorker could later collapse all
  tabs onto one connection *without changing the routing model* if needed.
  That is an optimisation, explicitly out of scope for the initial build.
- **TanStack Query cache is per-tab** (it lives in tab memory). This is
  desirable here - tabs stay isolated.

**Bonus**: because each tab is just the SPA at a different URL,
"pop this view out into its own window" is essentially free
(`window.open('/summit/lsstcam/mosaic')`) - useful for multi-monitor
observing stations.

---

### Phase 1: Foundation

**Goal**: A project skeleton that compiles, runs, and has a fast dev loop -
backend serves a stub API, frontend boots and routes, the two talk over a
dev proxy. No real S3 data yet; the point is to nail the structure, types,
and tooling so every later phase drops into a known shape.

**Exit criteria**:

- `uvicorn` serves the app; `GET /api/health/live` returns 200.
- Vite dev server renders the shell and deep-links resolve on hard reload.
- Config loads from YAML into typed Pydantic models and fails loudly on
  invalid config.
- `pytest` and the frontend test runner both run green in CI.

#### Backend

Proposed package layout (flat, feature-first, no god-modules):

```
rubintv/
  __init__.py
  main.py              # uvicorn entrypoint
  app.py               # create_app() factory + lifespan
  config/
    settings.py        # Pydantic Settings (env + file)
    models.py          # Location, Camera, Channel, Service (Pydantic v2)
    loader.py          # parse + validate models_data.yaml -> models
  s3/
    client.py          # S3ClientPool: one client per location
  api/
    health.py          # /api/health/live, /api/health/ready
    deps.py            # FastAPI dependencies (get_store, get_models)
  logging.py           # structlog config
```

- [ ] Package structure as above (modules small, one responsibility each)
- [ ] `create_app()` factory + `lifespan` that wires nothing real yet
      (placeholder store), so startup order is established early
- [ ] **Config split** into two concerns:
  - `Settings` (Pydantic Settings): runtime/env - site name, bucket
    overrides, PVC path, Redis URL, log level, poll intervals
  - `models_data.yaml` loaded + **validated** into typed `Location` /
    `Camera` / `Channel` / `Service` models (replace today's loose dict
    parsing; fail at startup on unknown camera refs, bad colours, etc.)
- [ ] `Camera` / `Location` / `Channel` Pydantic v2 models with the fields
      from [§3](#3-data-model--s3-bucket-structure) (per_day, colour, icon,
      label, camera_groups, metadata_columns)
- [ ] `S3ClientPool`: one pooled client per location, async-friendly,
      created in lifespan, closed on shutdown
- [ ] `/api/health/live` (process up) and `/api/health/ready` (returns
      not-ready until first poll completes - wired in Phase 2/7)
- [ ] structlog configured (JSON in prod, pretty in dev)
- [ ] Dockerfile (multi-stage: build deps -> slim runtime)
- [ ] pytest + `moto` for S3 mocking; a fixture that stands up a fake
      bucket with a handful of well-formed keys

#### Frontend

Proposed layout (route-per-view, shared `lib/` for cross-cutting code):

```
web/src/
  main.tsx             # React root, Router, QueryClientProvider
  routes.tsx           # path-based route table (see Decision 7)
  lib/
    api.ts             # typed fetch client (generated types from OpenAPI)
    queryClient.ts     # TanStack Query config + staleTime tiers
    ws.ts              # useWebSocket() - one connection per tab
    types.ts           # shared API types (generated)
  components/          # Layout, Breadcrumbs, ConnectionStatus, skeletons
  views/               # Home, Location, CameraTable, Channel, ... (Phase 5)
```

- [ ] Vite + React + TypeScript scaffold
- [ ] React Router with **path-based** routes (no hash) matching the
      current URL structure; a catch-all so deep links work
      (see [Decision 7](#decision-7---multi-tab--multi-window))
- [ ] TanStack Query provider + the staleTime tiers from
      [Appendix A](#recommended-caching-strategy) centralised in one config
- [ ] `useWebSocket()` skeleton: **one connection per tab**, reconnecting,
      typed messages, route-driven subscribe/unsubscribe
- [ ] Vite dev proxy: `/api` and `/ws` -> FastAPI, so dev is single-origin
- [ ] Layout shell: header with breadcrumbs, nav, content area,
      connection-status indicator, skeleton placeholders (not spinners)

#### Shared

- [ ] **API contract is the seam**: FastAPI generates the OpenAPI schema;
      the frontend generates TypeScript types from it (e.g.
      `openapi-typescript`). Types are never hand-written on both sides.
- [ ] CI: backend (ruff + mypy + pytest), frontend (eslint + tsc + vitest +
      build), and an OpenAPI-types-are-in-sync check

### Phase 2: Data Layer

**Goal**: The server ingests S3 data, maintains an in-memory index that is
the single source of truth for the API, and persists it for fast restarts.
No HTTP API yet - this phase is the internal data store and the tasks that
fill it. It is the heart of the rebuild and where the old design's coupling
gets untangled.

**The central idea**: separate the three things the old `CurrentPoller`
fused together - **getting objects** (a `DataSource`), **indexing them**
(the `EventStore`), and **telling people they changed** (the `EventBus`).
Each has one job and a narrow interface, so polling vs. Kafka, or
WebSocket vs. anything else, are swaps at the edges.

```
DataSource ──emits ObjectEvent──▶ EventStore ──emits StoreChange──▶ EventBus
 (poll/kafka)                      (index, dedupe,                  (fan-out to
                                    parse, sieve)                    WS, API cache)
```

**Exit criteria**:

- Point the poller at the moto/fixture bucket; the `EventStore` ends up
  with the correct structured-data index, extension info, per-day data,
  metadata, and calendar.
- Removing an object from the bucket is reflected on the next cycle.
- Kill and restart the process: it warm-starts from the cache file and
  reconciles against S3, never serving stale-only data as truth.

#### Ingestion

The `DataSource` is the only thing that knows *how* objects arrive. It
emits a normalised `ObjectEvent { kind: created|removed, key, etag, size }`
- nothing downstream cares whether that came from a poll diff or a Kafka
message.

- [ ] `DataSource` protocol: async iterator / callback emitting
      `ObjectEvent`s, plus a `snapshot()` for full-scan bootstrapping
      (see [Decision 1](#decision-1-s3-ingestion-strategy))
- [ ] `S3Poller(DataSource)`: lists a prefix, **diffs against the previous
      listing** to synthesise created/removed events (ETag change = update).
      Parallel listing with a bounded thread/async pool, reverse-chrono
      order so recent dates land first
- [ ] (Future, not initial build) `KafkaSource(DataSource)` consuming the
      summit `lsst.s3.rubin.tv` topic; emits the same `ObjectEvent`s
      directly. Selected per-site by config - zero downstream change
- [ ] **Key parser**: regex `{camera}/{day_obs}/{channel}/{seq}/{file}` and
      the metadata / night_report variants. Returns `None` for
      non-conforming keys, which are **silently ignored** (confirmed safe)
- [ ] **Sieve**: route each parsed object to metadata.json handling,
      night_report handling, or channel-event handling
- [ ] Per-day channel handling (`seq_num == "final"` etc.)
- [ ] Tolerant of seq_num gaps (sparse ints, never assume contiguity,
      <10,000/day) and of multiple independent producers (no cross-producer
      ordering guarantee - never assume "if N exists, N-1 exists")

#### In-Memory Store

`EventStore` is the single source of truth the API will read from. It owns
the indexes; nothing else mutates them. It consumes `ObjectEvent`s and
emits coarse `StoreChange`s (e.g. "camera X date Y structured-data
changed") so listeners refetch/repush the right slice.

- [ ] `EventStore` holding, keyed by `(location, camera)`:
  - Structured-data index: `{date: {channel: set[seq]}}` - "what exists"
  - Extension info: `{date: {channel: ExtInfo}}` - construct keys without
    a per-object query
  - Night-report index: `{date: NightReport}` (internal name kept; UI label
    is neutral - see [Phase 5 Pages](#pages))
  - Calendar: `sorted[date]`
  - Current-day state (subsumes the old `CurrentPoller` dicts)
- [ ] Apply `ObjectEvent`: created/updated inserts into the index, removed
      deletes from it (and prunes now-empty channels/dates so the calendar
      stays accurate)
- [ ] `EventBus`: in-process async pub/sub. `EventStore` publishes
      `StoreChange`; subscribers (WS handler in Phase 4, query-cache
      invalidation hints) react. Decouples ingestion from notification so
      the data path doesn't know a WebSocket exists
- [ ] Concurrency: reads (API) and writes (poller) interleave - use
      per-`(loc,cam)` locks or copy-on-read snapshots so the API never sees
      a half-applied update

#### Cache Persistence

A **warm-start optimisation only** - never authoritative.

- [ ] Serialize the `EventStore` indexes to disk. Prefer a **file-per
      `(location, camera, date)`** layout over one monolithic blob, so a
      single changed day rewrites one small file rather than reserializing
      everything (the old pickle's main pain). JSON keeps it debuggable;
      revisit a binary format only if size/throughput demands it
- [ ] Load on startup if a (PVC) cache dir exists; otherwise skip silently
- [ ] **Graceful fallback**: missing, partial, or corrupt cache must never
      crash startup - log, discard the bad slice, rebuild that slice from S3
- [ ] **Version tag** in the on-disk format; a version mismatch discards the
      cache rather than mis-parsing it
- [ ] A PVC write failure mid-run is non-fatal (the cache is best-effort)

Note: Historical data is mutable. Yesterday's data changes frequently
(analysis backlogs clearing). Even older dates can gain or lose fields at
any point. The historical scanner must re-check recent dates on every
cycle, not just on first load. The cache is a startup speed-up, not a
source of truth - S3 is always authoritative, so every load is reconciled
against a real scan.

#### Background Tasks

Owned by the lifespan; all push into the `EventStore` via a `DataSource`,
so they share one code path and differ only in *what* they scan and *how
often*.

- [ ] **Current-day poller** (~1s): scans today's prefixes for every
      `(loc, cam)`, feeds the `EventStore`
- [ ] **Historical scanner**: full scan on startup (or after a cold cache),
      then a periodic refresh that **re-checks recent dates every cycle**
      (data mutates) and older dates more lazily
- [ ] **Yesterday poller** (~2m): catches delayed per-day artifacts (movies
      finalised after rollover)
- [ ] **Day-rollover logic**: when `get_current_day_obs()` (UTC-12) ticks,
      integrate today's state into history, reset current-day state, and
      keep watching yesterday for stragglers. Centralise this - it was a
      fragile corner of the old design
- [ ] **Metadata fetching**: LRU cache (~60 days/cam), per-key async lock to
      dedupe concurrent fetches, ETag-gated re-download, background prefetch
      that yields to live user requests
- [ ] **Readiness gate**: `/api/health/ready` flips to ready only after the
      first current-day poll completes (wired here, surfaced in Phase 7)

### Phase 3: API

**Goal**: A complete, typed REST API reading from the `EventStore`, so the
frontend can fetch everything it needs over plain HTTP. Endpoints are thin -
they format what the store already holds; no S3 access on the request path
except the proxy.

**Exit criteria**:

- Every endpoint below returns validated Pydantic response models and so
  appears in the generated OpenAPI schema (and thus in the frontend types).
- The full set is exercised against a moto-backed store in tests.
- Hitting an unknown location/camera/date returns a clean 404, not a 500.

**Conventions** (apply across all endpoints):

- All paths under `/api`. Path params validated (`loc`, `cam` against the
  configured models; `date` as `YYYY-MM-DD`; unknown values -> 404).
- Responses are typed Pydantic models -> the OpenAPI schema is the source
  of the frontend's TS types (the seam from [Phase 1](#shared)).
- Read-only endpoints carry cache headers aligned to the
  [staleTime tiers](#recommended-caching-strategy); the response also echoes
  the data's ETag/hash where one exists so the client can revalidate.
- orjson responses; gzip negotiated via standard middleware.

#### Core Endpoints

- [ ] `GET /api/locations` - all locations visible to this site
- [ ] `GET /api/locations/{loc}` - single location with its camera groups
- [ ] `GET /api/locations/{loc}/cameras/{cam}` - camera detail (channels,
      metadata-column definitions, flags like per_day / mosaic / allsky)
- [ ] `GET /api/locations/{loc}/cameras/{cam}/dates/{date}` - the page
      payload: structured data + extension info + metadata + per-day +
      whether a night report exists. One round-trip renders the table
- [ ] `GET /api/locations/{loc}/cameras/{cam}/channels/{chan}/current` -
      most recent event for a channel (drives the channel view's default)
- [ ] `GET /api/locations/{loc}/cameras/{cam}/events?key=...` - resolve a
      specific event by its S3 key (key validated against the parser)

#### Night Reports

> Internal/route name kept as `night-report` (mirrors the S3 prefix); the
> UI renders a neutral label - see [Phase 5 Pages](#pages).

- [ ] `GET /api/locations/{loc}/cameras/{cam}/night-report` - current day
- [ ] `GET /api/locations/{loc}/cameras/{cam}/night-report/{date}` -
      historical (immutable once past, so cacheable)

#### Metadata

- [ ] `GET /api/locations/{loc}/cameras/{cam}/metadata/{date}` - the
      seq_num -> {column: value} map for a date

#### Calendar

- [ ] `GET /api/locations/{loc}/cameras/{cam}/calendar` - all dates with
      data (the full back-catalogue must be reachable - history matters)

#### Redis / Admin

- [ ] `GET /api/admin/controls` - current control readback values
- [ ] `POST /api/admin/controls` - set a control value. **Gated on the
      admin user list** (per-location `admin_for`); writes the Redis key and
      returns the accepted value (readback arrives later over WS)
- [ ] `POST /api/admin/reset-historical` - trigger a full rescan
      (admin-gated; idempotent - a rescan already running is a no-op)

#### S3 Proxy

- [ ] `GET /api/locations/{loc}/cameras/{cam}/channels/{chan}/{date}/{seq}/{filename}` -
      stream the S3 object through with **ETag-based revalidation** (honour
      `If-None-Match`, return 304 when unchanged) and the
      `Cache-Control` policy from [Appendix A](#image-caching-http-level).
      Range requests passed through for video scrubbing. The key is built
      from path params and validated before any S3 call

### Phase 4: Real-Time

**Goal**: Live updates flow from server to browser without polling. The
`EventBus` from [Phase 2](#in-memory-store) is the source; the WebSocket
handler is just one bus subscriber that fans changes out to interested
clients.

**Exit criteria**:

- A new object landing in S3 appears in a subscribed client within one poll
  cycle, with no client-side polling.
- Subscriptions are scoped: a client subscribed to camera A gets nothing
  for camera B.
- A slow or dead client is detected and dropped without stalling the bus or
  other clients.

#### WebSocket Server

- [ ] **Single** endpoint `/ws` (one connection per tab - see
      [Decision 7](#decision-7---multi-tab--multi-window))
- [ ] **Typed JSON protocol** (no stringly-typed messages). Sketch:

```jsonc
// client -> server
{ "action": "subscribe",   "topic": "camera",   "location": "summit", "camera": "lsstcam" }
{ "action": "unsubscribe", "topic": "channel",  "location": "summit", "camera": "lsstcam", "channel": "witness_detector" }

// server -> client
{ "type": "channelData", "location": "summit", "camera": "lsstcam", "data": { /* structuredData + extensionInfo */ } }
{ "type": "error",       "message": "unknown camera" }
```

  Both directions are Pydantic models so the schema is shared with the
  frontend the same way the REST types are.
- [ ] **Connection manager**: tracks live sockets, assigns a connection id,
      handles heartbeat/ping so dead sockets are reaped
- [ ] **Subscription registry**: `topic -> set[connection]`, so fan-out is a
      dict lookup, not a scan of all clients. Subscriptions are validated
      against the configured models (bad topic -> `error`, not a crash)
- [ ] **Backpressure**: per-connection send queue with a bounded size; if a
      client can't keep up, drop it rather than buffering unboundedly

#### Integration with EventStore

- [ ] WS handler subscribes to the `EventBus` and translates each
      `StoreChange` into the right client message(s) for the matching topic
- [ ] Message types (payloads validated):
  - `channelData` - structured data + extension info changed
  - `event` - new event in a channel
  - `metadata` - metadata.json updated
  - `perDay` - per-day channel data changed
  - `nightReport` - night report changed (UI label stays neutral)
  - `dayChange` - day rolled over (clients reset current-day views)
  - `detectorStatus` - cluster worker status
  - `controlReadback` - admin control value changed
  - `calendarUpdate` - a new date appeared in the calendar
- [ ] On (re)subscribe, the server sends the **current snapshot** for that
      topic immediately, then deltas - so a freshly opened tab is correct
      without waiting for the next change

#### Redis Integration

Redis is just another `DataSource`-shaped input to the bus, so live status
flows through the same path as S3 data.

- [ ] Detector-status stream reader (Redis streams -> `detectorStatus`)
- [ ] Control-readback subscriber (keyspace events on `*_READBACK` ->
      `controlReadback`)
- [ ] Both publish onto the same `EventBus`; the WS handler doesn't know or
      care that the origin was Redis rather than S3
- [ ] Redis is **optional**: absent Redis disables detector/admin live
      updates with a clear logged warning, but the app still serves S3 data
      (fixing the old "silent degradation")

#### Frontend WebSocket Hook

- [ ] `useWebSocket()` hook that manages connection, reconnection,
      and subscription lifecycle - **one connection per tab** (see
      [Decision 7](#decision-7---multi-tab--multi-window))
- [ ] Subscriptions are driven by the current route: a tab subscribes only
      to the data the view it is showing needs, and resubscribes on
      navigation
- [ ] Integrates with TanStack Query: WebSocket updates can invalidate
      or directly update cached query data (cache is per-tab)

### Phase 5: Frontend

**Goal**: Feature-complete SPA matching (and improving on) all current views.

This is a full client-side-routed React SPA. See
[Decision 4](#decision-4-frontend---react-spa) and the
[Multi-Tab / Multi-Window](#decision-7---multi-tab--multi-window) decision
for the rationale and the constraints it imposes (path-based routing,
per-tab WebSocket, no shared singleton state).

**Exit criteria**:

- Every view below is reachable by a deep link that restores its exact
  state on hard reload (the multi-tab guarantee).
- Each view fetches its initial data via TanStack Query and applies live
  deltas from the WebSocket; no view polls.
- Stale-while-revalidate everywhere: navigating to a previously seen view
  shows cached data instantly, refreshes silently.

**Route table** (path = full description of a tab's state):

| Path                                  | View          |
| ------------------------------------- | ------------- |
| `/`                                   | Home          |
| `/{location}`                         | Location      |
| `/{location}/{camera}`                | Camera Table  |
| `/{location}/{camera}/{channel}`      | Channel View  |
| `/{location}/{camera}/night-report`   | Night Report  |
| `/{location}/{camera}/allsky`         | All Sky       |
| `/{location}/{camera}/detectors`      | Detectors     |
| `/{location}/{camera}/admin`          | Admin         |
| `/{location}/{camera}/mosaic`         | Mosaic/Movies |

#### App Shell

- [ ] Layout: header with location/camera breadcrumbs, nav
- [ ] React Router routes matching current URL structure (path-based;
      backend serves a catch-all -> `index.html` so deep links survive a
      hard reload)
- [ ] Loading states: skeleton screens, not spinners (user always sees
      the page structure immediately)
- [ ] Error boundaries with retry
- [ ] WebSocket connection status indicator

#### Pages

**Home** (`/`):

- [ ] Location grid (cards with logos)

**Location** (`/{location}`):

- [ ] Camera groups with camera cards
- [ ] Online/offline status indicators

**Camera Table** (`/{location}/{camera}`):

- [ ] Date picker (calendar with available dates highlighted)
- [ ] Data table: seq_num rows, channel columns, clickable cells
- [ ] Metadata columns (user-configurable, persisted to localStorage)
- [ ] Per-day channel display (movies, etc.)
- [ ] Night report link (when available)
- [ ] Time-since-last-image clock
- [ ] Live updates via WebSocket (new rows appear, no reload)
- [ ] Copy-row-template button

**Channel View** (`/{location}/{camera}/{channel}`):

- [ ] Image/video display for current or selected event
- [ ] Prev/next navigation between sequence numbers
- [ ] Channel switcher (other channels for same seq_num)
- [ ] Metadata sidebar for current seq_num
- [ ] Image viewer link (external)
- [ ] Live updates (new image auto-displays)

**Night Report** (`/{location}/{camera}/night-report`):

> **UI naming**: Do **not** use the phrase "night report" in user-facing
> copy - the term can read as judgemental. Display a neutral label
> instead. The backend, API routes, and S3 key prefix keep the existing
> `night_report` / `night-report` terminology (it mirrors the S3 layout
> and avoids a churny rename); only the rendered label differs. Pick the
> neutral display string in one place (a constant) so it can be changed
> centrally.

- [ ] Text sections (multiline, key-values, links) - can be added and
      updated during the night; historical reports are not expected to
      mutate
- [ ] Plot gallery with grouping - plots can be added/updated during the
      night
- [ ] Date picker for historical reports
- [ ] Live updates during the night

**All Sky** (`/{location}/{camera}/allsky`):

- [ ] Current image display
- [ ] Movie playback
- [ ] Date picker

**Detectors** (`/{location}/{camera}/detectors`):

- [ ] Detector worker status cards (colour-coded)
- [ ] Live updates from Redis streams

**Admin** (`/{location}/{camera}/admin`):

- [ ] Control menus (AOS pipeline, chip selection, etc.)
- [ ] Current readback values
- [ ] Live readback updates
- [ ] Admin user gating

**Mosaic/Movies** (`/{location}/{camera}/mosaic`):

- [ ] Grid of per-day media with metadata columns

#### Cross-Cutting Concerns

- [ ] TanStack Query caching strategy - **date-tiered**, because historical
      data is *mutable* (yesterday churns; older dates can still change).
      Full table in [Appendix A](#recommended-caching-strategy); in short:
  - Config (locations, cameras): `staleTime: Infinity` - static
  - Today's data: `staleTime: 0` - WebSocket-driven, refetch freely
  - Yesterday: ~30s · last week: ~2min · older: ~5min (revalidate; always
    show stale while fetching)
  - Calendar: ~5min · night report: ~2min
- [ ] WebSocket-to-Query bridge: live messages `setQueryData`/invalidate the
      matching cache key so live views update without an extra fetch
- [ ] Image preloading for prev/next navigation (prefetch neighbouring seq)
- [ ] Responsive design (works on tablets for summit use)
- [ ] Keyboard navigation (arrow keys for prev/next)
- [ ] Column preferences persisted to localStorage (per camera)

### Phase 6: Sub-Apps

**Goal**: DDV and exp_checker integrated as mounted sub-apps, sharing the
shell's navigation but otherwise self-contained (see
[Decision 6](#decision-6-scope---ddv-and-exp_checker-included)).

**Exit criteria**: both sub-apps load at their mount points, their links
back to the main SPA work, and neither blocks main-app startup if it fails
to initialise.

- [ ] **DDV (Flutter)**: serve its built assets at `/ddv`; bridge its
      WebSocket needs. Treat it as an opaque embedded app - the main app
      provides the route and the connection, not the internals
- [ ] **exp_checker**: mount as a FastAPI sub-app at `/exp_checker`,
      sharing the same uvicorn process and lifespan
- [ ] Shared nav: a link/affordance to reach each sub-app from the shell,
      and a way back. Since the SPA is path-routed, links are just URLs
- [ ] Sub-app failure isolation: a sub-app that errors on mount logs and is
      skipped; the main app still serves

### Phase 7: Operational Readiness

**Goal**: Production-grade deployment - the app starts predictably with or
without a PVC, reports health honestly, shuts down cleanly, and can be
rolled out alongside the old app for comparison.

**Exit criteria**:

- Pod with **and** without a PVC both reach ready and serve correct data
  (cache is purely a speed-up).
- `kubectl rollout` drains cleanly: in-flight WS clients are closed and the
  cache is flushed.
- Old and new run side by side against the same buckets and produce
  matching table/calendar/night-report output for spot-checked dates.

- [ ] Structured logging (structlog; JSON in prod) with request/connection
      correlation ids
- [ ] Health endpoints: `/api/health/live` (process up) and
      `/api/health/ready`
- [ ] **Readiness gate**: not-ready until the first current-day poll
      completes, so k8s doesn't route traffic to an empty store
- [ ] **Graceful shutdown**: stop accepting new WS connections, close
      existing ones with a clean code, cancel background tasks, flush the
      cache to the PVC if present
- [ ] **Cache-warming strategy** (the with/without-PVC split):
  - With PVC: load the cache, serve immediately, reconcile against S3 in
    the background (cache is never trusted as truth)
  - Without PVC: full S3 scan; serve config and live data right away and
    stream historical in as it loads
  - Frontend shows a non-blocking "historical still loading" affordance,
    never an empty-looking error
- [ ] Surface a `historicalStatus` (busy/idle) over the WS so the frontend
      knows when the back-catalogue is still filling
- [ ] Dockerfile: multi-stage (Node build of the SPA -> Python runtime
      serving API + static assets)
- [ ] **Migration plan**: run old and new in parallel; diff their API/table
      output for a set of dates and cameras before cutover
- [ ] Metrics/observability: at minimum poll-cycle duration, S3 call
      counts, WS connection count, cache hit/miss on warm start
- [ ] Documentation: auto-generated API docs (OpenAPI) + an operator guide
      (env vars, PVC behaviour, Redis-optional behaviour, rollback)

---

## Appendix A: Frontend Caching in Detail

This section expands on the client-side caching question from Phase 0.

### The Two Kinds of Data

RubinTV has two fundamentally different data flows, but neither is truly
immutable:

1. **Historical data** (REST API): Dates in the past. Yesterday's data is
   likely to change as analysis backlogs clear. Even older data can be
   supplemented with new fields or have data removed at any point. This
   rules out "cache forever" strategies but still benefits from
   stale-while-revalidate: show what we have, refresh in the background.

2. **Live data** (WebSocket): Today's data. Changes every second. Must be
   pushed, not polled.

### How TanStack Query Works

TanStack Query (formerly React Query) manages a client-side cache of API
responses. Each API call gets a "query key" (like a cache key):

```tsx
// This fetches once, then serves from cache for 5 minutes
const { data } = useQuery({
  queryKey: ["camera-data", location, camera, date],
  queryFn: () => api.getCameraData(location, camera, date),
  staleTime: 5 * 60 * 1000, // consider fresh for 5 min
})
```

Key behaviours:

- **Deduplication**: If two components request the same data, only one fetch
  happens.
- **Stale-while-revalidate**: Shows cached data immediately, refetches in
  background.
- **Automatic garbage collection**: Unused cache entries are freed.
- **Invalidation**: WebSocket messages can trigger targeted cache updates.

### Recommended Caching Strategy

Historical data is **not immutable**. Yesterday's data changes as analysis
backlogs clear, and even older dates can gain new fields or lose data at
any time. The caching strategy must account for this:

| Data Type                   | Query Key                             | staleTime | Notes                             |
| --------------------------- | ------------------------------------- | --------- | --------------------------------- |
| Locations / cameras         | `['locations']`                       | Infinity  | Static config, loaded once        |
| Camera data for yesterday   | `['camera', loc, cam, date]`          | 30s       | Likely changing, revalidate often |
| Camera data for older dates | `['camera', loc, cam, date]`          | 5 min     | Can change, but less frequently   |
| Camera data for today       | `['camera', loc, cam, 'today']`       | 0         | WebSocket updates                 |
| Metadata for yesterday      | `['metadata', loc, cam, date]`        | 30s       | Same as camera data               |
| Metadata for older dates    | `['metadata', loc, cam, date]`        | 5 min     | Can change                        |
| Night report (any date)     | `['night-report', loc, cam, date]`    | 2 min     | Can be updated retroactively      |
| Calendar                    | `['calendar', loc, cam]`              | 5 min     | Grows slowly                      |
| Current channel event       | Managed by WebSocket state, not Query | N/A       | Pure push                         |

The key principle is **stale-while-revalidate**: the user sees cached data
instantly (no spinner), and a background refetch updates the display if
anything changed. The `staleTime` values control how aggressively we
recheck, not how long data is _displayed_ - stale data is always shown
while fresh data loads.

A simple heuristic determines the tier:

```tsx
function staleTimeForDate(date: Date): number {
  const daysAgo = daysSince(date)
  if (daysAgo <= 1) return 30 * 1000 // yesterday: 30s
  if (daysAgo <= 7) return 2 * 60 * 1000 // last week: 2 min
  return 5 * 60 * 1000 // older: 5 min
}
```

If S3 event notifications become available in the future, the server could
push invalidation hints over the WebSocket ("date X changed for camera Y"),
allowing the frontend to instantly refetch only what changed rather than
relying on time-based staleness.

### WebSocket + Query Integration

The real power comes from combining them. When a WebSocket message arrives
saying "new data for lsstcam today", TanStack Query can:

```tsx
// In your WebSocket handler:
queryClient.setQueryData(["camera", "summit-usdf", "lsstcam", "today"], (old) =>
  mergeNewData(old, wsMessage.data)
)
```

This updates the cached data _without_ an API call. The UI re-renders
instantly. The user sees new rows appear in the table in real time.

### Image Caching (HTTP Level)

For proxied S3 images, the server should set Cache-Control headers.
Since even historical images could theoretically be replaced, we use
ETag-based revalidation rather than `immutable`:

```
# All images: cache, but revalidate with ETag (S3 provides ETags)
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
ETag: "s3-object-etag-here"
```

On subsequent requests, the browser sends `If-None-Match` with the ETag.
If the S3 object hasn't changed (same ETag), the server responds with
304 Not Modified (no body, instant). If it has changed, the new image
is sent. This gives near-instant navigation for unchanged images while
still picking up replacements.

### What This Means for the User Experience

- Navigating between dates feels instant (cached data renders immediately,
  even if a background refresh is in flight)
- Navigating back to a previously viewed page shows data immediately
- If historical data changed since last visit, the update appears
  seamlessly after the background refetch completes (no spinner, no flash)
- Today's page updates live without any user action
- Images that were already viewed load from browser cache (or revalidate
  via ETag with a 304, which is nearly as fast)
- The app feels responsive at every stage because there's always _something_
  to show (stale data while fresh data loads)
- Future upgrade path: if S3 event notifications land, the server can push
  targeted invalidation hints ("camera X, date Y changed") and the
  frontend refetches just that data instantly

---

## Appendix B: Resolved Questions

The original open questions have been answered. The answers are folded into
the relevant plan sections above; this appendix records them for reference.

### S3 Bucket Contents

1. **What writes to the S3 buckets?**

   **Multiple independent producers.** seq_num generation is not our
   concern: they are incrementally assigned integers, occasionally skipping
   one or two (harmless for us), and never exceed ~10,000 on a given day.
   The team maintaining the producer code is reachable, so any object
   naming issues can be resolved by dialogue rather than defensive parsing.
   *Design impact*: the ingestion layer must tolerate seq_num gaps and must
   not assume a single writer (no global ordering guarantee across
   producers). See [Phase 2 - Ingestion](#ingestion).

2. **Are there S3 objects that don't follow the documented key patterns?**

   **No.** Anything in the bucket that doesn't match the rules can be
   **safely ignored** by the parser. See [Phase 2 - Ingestion](#ingestion).

3. **How many days of history matter?**

   **All of it** must be viewable (history goes back to 2020-01-01). This
   reinforces the [Phase 7](#phase-7-operational-readiness) cache-warming
   and historical-loading-state requirements - the full back-catalogue is
   in scope, not just recent dates.

4. **S3 event notifications on Ceph.**

   **Summit now has a Kafka-connected topic; USDF expected soon.** This is
   now reflected as the planned next `DataSource` in
   [Decision 1](#decision-1-s3-ingestion-strategy), which reproduces the
   `CephBucketNotification` manifest. Polling remains the initial,
   works-everywhere baseline.

### "Night Reports" (UI naming - see below)

5. **Who/what generates them, and can they change?**

   Plots **and** text files can be **added and updated during the night**.
   Historical days are **not expected to mutate**. *Crucially*: the phrase
   "night report" must **not** appear in user-facing copy - it can read as
   judgemental. Backend/API/S3 keep `night_report`; only the displayed
   label is neutral. See the UI-naming note in
   [Phase 5 - Pages](#pages).

### Redis

6. **What are the control keys for?**

   The same Rapid Analysis reads the control keys and supplies the
   `_READBACK` values. **We don't need to know their meaning.** Setting them
   affects future plots, which is **out of scope** for RubinTV - we only
   read/write the values and display the readback.
