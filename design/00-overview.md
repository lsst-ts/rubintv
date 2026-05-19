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

**Status**: Polling (with S3 event notifications as a future upgrade path).

The S3 buckets are Ceph-based. Bucket notification sinks are being
investigated at both USDF and summit, but availability and configuration
may differ per site. The architecture should:
- Start with polling (proven, works everywhere)
- Abstract the ingestion interface so event-driven can be swapped in later
- Design the internal event flow as push-based (poller pushes into an event
  bus), so the switch from "poll then push" to "notification then push"
  only changes the source, not the downstream logic

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
- **SQLite consideration**: SQLite on PVC *could* replace the pickle cache
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
fetching libraries provide sophisticated client-side caching *without*
any server involvement. This is one of the biggest wins of the rebuild.
Here's how the landscape breaks down:

| Approach | What it does | Best for |
|----------|-------------|----------|
| **React Query (TanStack Query)** | Caches API responses in browser memory. Automatic refetching, stale-while-revalidate, background refresh, deduplication. | REST API data: historical dates, metadata, night reports, calendar |
| **WebSocket state** | Live data pushed by server, held in React state/context | Today's data: current events, structured data, detector status |
| **Browser Cache-Control** | HTTP cache headers on proxied S3 images | Images/videos: once an image for seq 42 exists, it never changes |

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

---

### Phase 1: Foundation

**Goal**: New project skeleton with core infrastructure that compiles,
runs, and has a working dev loop.

#### Backend
- [ ] New Python package structure (cleaner module layout)
- [ ] FastAPI app factory with lifespan
- [ ] Configuration model (Pydantic Settings, replace `models_data.yaml`
      parsing with validated, typed config)
- [ ] Camera/Location/Channel model definitions (Pydantic v2)
- [ ] S3 client abstraction with connection pooling
- [ ] Docker build
- [ ] pytest infrastructure with moto for S3 mocking

#### Frontend
- [ ] Vite + React + TypeScript project
- [ ] React Router with route structure matching current pages
- [ ] TanStack Query setup with API client
- [ ] WebSocket client (reconnecting, typed messages)
- [ ] Dev proxy to backend API (Vite dev server -> FastAPI)
- [ ] Basic layout shell (header, nav, content area)

#### Shared
- [ ] Define the API contract (OpenAPI schema generated from FastAPI)
- [ ] CI pipeline (lint, type-check, test, build)

### Phase 2: Data Layer

**Goal**: The server can ingest S3 data, maintain an in-memory index, and
persist it for fast restarts. No API yet - just the internal data store.

#### Ingestion
- [ ] S3 poller: abstract `DataSource` interface, concrete `S3Poller`
- [ ] Event parser (same regex-based key parsing, but cleaner)
- [ ] Object sieving: separate metadata, night reports, channel events
- [ ] Per-day channel handling

#### In-Memory Store
- [ ] `EventStore` class: the single source of truth for all indexed data
  - Structured data index: `{(loc, cam): {date: {channel: set[seq]}}}`
  - Extension info: `{(loc, cam): {date: {channel: ExtInfo}}}`
  - Night report index: `{(loc, cam): {date: NightReport}}`
  - Calendar: `{(loc, cam): sorted[date]}`
  - Current day state (replaces CurrentPoller's dicts)
- [ ] Event bus: internal pub/sub so the store can notify listeners
      when data changes (decouples ingestion from notification)

#### Cache Persistence
- [ ] Serialize store to disk (JSON or structured format)
- [ ] Load from disk on startup if available
- [ ] Graceful fallback: if no cache, rebuild from S3
- [ ] Cache invalidation / versioning

Note: Historical data is mutable. Yesterday's data changes frequently
(analysis backlogs clearing). Even older dates can gain or lose fields
at any point. The historical scanner must re-check recent dates on every
cycle, not just on first load. The server-side cache is a performance
optimisation for startup, not a source of truth - S3 is always
authoritative.

#### Background Tasks
- [ ] Current-day poller (~1s loop, same as today)
- [ ] Historical scanner (full scan on startup, periodic refresh)
- [ ] Yesterday poller (for delayed per-day artifacts)
- [ ] Day rollover logic
- [ ] Metadata fetching with LRU cache + background prefetch

### Phase 3: API

**Goal**: Complete REST API. The frontend can fetch everything it needs.

#### Core Endpoints
- [ ] `GET /api/locations` - all locations
- [ ] `GET /api/locations/{loc}` - single location with cameras
- [ ] `GET /api/locations/{loc}/cameras/{cam}` - camera detail
- [ ] `GET /api/locations/{loc}/cameras/{cam}/dates/{date}` -
      structured data + extension info + metadata + per-day + NR exists
- [ ] `GET /api/locations/{loc}/cameras/{cam}/channels/{chan}/current` -
      most recent event
- [ ] `GET /api/locations/{loc}/cameras/{cam}/events?key=...` -
      specific event by key

#### Night Reports
- [ ] `GET /api/locations/{loc}/cameras/{cam}/night-report` - current
- [ ] `GET /api/locations/{loc}/cameras/{cam}/night-report/{date}` -
      historical

#### Metadata
- [ ] `GET /api/locations/{loc}/cameras/{cam}/metadata/{date}` -
      metadata for a date

#### Calendar
- [ ] `GET /api/locations/{loc}/cameras/{cam}/calendar` -
      all dates with data

#### Redis / Admin
- [ ] `GET /api/admin/controls` - current control values
- [ ] `POST /api/admin/controls` - set a control value
- [ ] `POST /api/admin/reset-historical` - trigger full rescan

#### S3 Proxy
- [ ] `GET /api/locations/{loc}/cameras/{cam}/channels/{chan}/{date}/{seq}/{filename}` -
      proxied S3 fetch with appropriate Cache-Control headers

### Phase 4: Real-Time

**Goal**: Live updates flow from server to browser without polling.

#### WebSocket Server
- [ ] Single WebSocket endpoint: `/ws`
- [ ] Typed message protocol (JSON schema, not stringly typed):
      ```
      Client -> Server: { "subscribe": "camera", "location": "...", "camera": "..." }
      Server -> Client: { "type": "channelData", "data": {...} }
      ```
- [ ] Connection manager with client tracking
- [ ] Subscription registry (which clients want which data)

#### Integration with EventStore
- [ ] EventStore emits events on the internal bus
- [ ] WebSocket handler listens to the bus and fans out to subscribers
- [ ] Message types:
  - `channelData` - structured data + extension info changed
  - `event` - new event in a channel
  - `metadata` - metadata.json updated
  - `perDay` - per-day channel data changed
  - `nightReport` - night report changed
  - `dayChange` - day rolled over
  - `detectorStatus` - cluster worker status
  - `controlReadback` - admin control value changed
  - `calendarUpdate` - new date appeared in calendar

#### Redis Integration
- [ ] Detector status stream reader (same as current)
- [ ] Control readback subscriber (same as current)
- [ ] Feed Redis events into the same internal event bus

#### Frontend WebSocket Hook
- [ ] `useWebSocket()` hook that manages connection, reconnection,
      and subscription lifecycle
- [ ] Integrates with TanStack Query: WebSocket updates can invalidate
      or directly update cached query data

### Phase 5: Frontend

**Goal**: Feature-complete SPA matching (and improving on) all current views.

#### App Shell
- [ ] Layout: header with location/camera breadcrumbs, nav
- [ ] React Router routes matching current URL structure
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
- [ ] Text sections (multiline, key-values, links)
- [ ] Plot gallery with grouping
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
- [ ] TanStack Query caching strategy:
  - Historical dates: `staleTime: Infinity` (data never changes)
  - Today's data: `staleTime: 0` (always refetch, but show stale while loading)
  - Calendar: `staleTime: 5min` (changes slowly)
  - Config data (locations, cameras): `staleTime: Infinity, cacheTime: Infinity`
- [ ] Image preloading for prev/next navigation
- [ ] Responsive design (works on tablets for summit use)
- [ ] Keyboard navigation (arrow keys for prev/next)

### Phase 6: Sub-Apps

**Goal**: DDV and exp_checker integrated.

- [ ] DDV Flutter app: mount at `/ddv`, WebSocket bridge
- [ ] exp_checker: mount as FastAPI sub-app at `/exp_checker`
- [ ] Shared navigation between main app and sub-apps

### Phase 7: Operational Readiness

**Goal**: Production-grade deployment.

- [ ] Structured logging (structlog, same as current)
- [ ] Health check endpoints (`/health/live`, `/health/ready`)
- [ ] Readiness gate: app reports not-ready until first poll completes
- [ ] Graceful shutdown (drain WebSocket connections, persist cache)
- [ ] Cache warming strategy:
  - With PVC: load from cache file, serve immediately, background refresh
  - Without PVC: full S3 scan, serve historical as it loads
  - Frontend handles "historical loading" state gracefully
- [ ] Dockerfile with multi-stage build (Python + Node)
- [ ] Migration plan: run old and new in parallel, compare outputs
- [ ] Documentation: API docs (auto-generated), operator guide

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
  queryKey: ['camera-data', location, camera, date],
  queryFn: () => api.getCameraData(location, camera, date),
  staleTime: 5 * 60 * 1000,  // consider fresh for 5 min
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

| Data Type | Query Key | staleTime | Notes |
|-----------|-----------|-----------|-------|
| Locations / cameras | `['locations']` | Infinity | Static config, loaded once |
| Camera data for yesterday | `['camera', loc, cam, date]` | 30s | Likely changing, revalidate often |
| Camera data for older dates | `['camera', loc, cam, date]` | 5 min | Can change, but less frequently |
| Camera data for today | `['camera', loc, cam, 'today']` | 0 | WebSocket updates |
| Metadata for yesterday | `['metadata', loc, cam, date]` | 30s | Same as camera data |
| Metadata for older dates | `['metadata', loc, cam, date]` | 5 min | Can change |
| Night report (any date) | `['night-report', loc, cam, date]` | 2 min | Can be updated retroactively |
| Calendar | `['calendar', loc, cam]` | 5 min | Grows slowly |
| Current channel event | Managed by WebSocket state, not Query | N/A | Pure push |

The key principle is **stale-while-revalidate**: the user sees cached data
instantly (no spinner), and a background refetch updates the display if
anything changed. The `staleTime` values control how aggressively we
recheck, not how long data is *displayed* - stale data is always shown
while fresh data loads.

A simple heuristic determines the tier:

```tsx
function staleTimeForDate(date: Date): number {
  const daysAgo = daysSince(date)
  if (daysAgo <= 1) return 30 * 1000      // yesterday: 30s
  if (daysAgo <= 7) return 2 * 60 * 1000  // last week: 2 min
  return 5 * 60 * 1000                     // older: 5 min
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
queryClient.setQueryData(
  ['camera', 'summit-usdf', 'lsstcam', 'today'],
  (old) => mergeNewData(old, wsMessage.data)
)
```

This updates the cached data *without* an API call. The UI re-renders
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
- The app feels responsive at every stage because there's always *something*
  to show (stale data while fresh data loads)
- Future upgrade path: if S3 event notifications land, the server can push
  targeted invalidation hints ("camera X, date Y changed") and the
  frontend refetches just that data instantly

---

## Appendix B: Remaining Questions

Some of the original questions remain open and would benefit from answers
as the rebuild progresses:

### S3 Bucket Contents

1. **What writes to the S3 buckets?** Is it a single "Rapid Analysis" pipeline,
   or multiple independent producers? How are seq_nums assigned?

2. **Are there any S3 objects that don't follow the documented key patterns?**
   (e.g. objects at the bucket root, objects with different path structures)

3. **How many days of history matter?** (Currently goes back to 2020-01-01.
   At up to ~5,000 objects/camera/day, how many cameras have data on a
   typical day?)

4. **S3 event notifications on Ceph**: Status of investigation into
   available sinks at USDF and summit.

### Night Reports

5. **Who/what generates night reports?** Are they generated during the night
   or after? Can plots be updated/added over the course of a night?

### Redis

6. **What are the control keys used for?** (AOS_PIPELINE, CHIP_SELECTION,
   etc.) Who reads the non-READBACK keys? (We know another app writes
   status to Redis and RubinTV is read-only for status streams.)
