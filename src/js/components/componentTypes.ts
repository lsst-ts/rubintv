import React from "react"
import * as Calendar from "calendar"

/** A single item of metadata is either a string, number or nested object of
 * key-value pairs. In the case of the latter, if one of the keys is
 * 'DISPLAY_VALUE', it's value is a UTF-8 encoded character to display as an
 * icon in a button in the table */
export type MetadatumType =
  | string
  | number
  | boolean
  | Record<string, string>
  | string[]

/**
 * @description Represents a row of metadata.
 * @example
 * const row: MetadataRow = {
 *   {
 *    DISPLAY_VALUE: "<UTF-8 encoded character>",
 *    VALUETOLIST1: 100,
 *    VALUETOLIST2: 200
 *   },
 *   "Exposure time": 30,
 *   "Location": "Living Room",
 * };
 */
export interface MetadataRow {
  [key: string]: MetadatumType
}

/**
 * @description Represents a collection of metadata rows.
 * @example
 * const metadata: Metadata = {
 *   "1": {
 *     "Exposure time": 30,
 *     "Location": "Living Room",
 *   },
 *   "2": {
 *     "Exposure time": 60,
 *     "Location": "Kitchen",
 *   },
 * };
 */
export interface Metadata {
  [seqNum: string]: MetadataRow
}

/**
 * @description Represents a column in a metadata table.
 * @param {string} name - The name of the column.
 * @param {string} [desc] - An optional description of the column.
 */
export interface MetadataColumn {
  name: string
  desc?: string
}

/**
 * @description Represents a single media item.
 * @param {string} key - A unique identifier for the media item in the bucket.
 * @param {string} hash - A hash value for the media item.
 * @param {string} camera_name - The name of the camera that captured the media.
 * @param {string} day_obs - The observation day of the media item.
 * @param {string} channel_name - The name of the channel associated with the media.
 * @param {string} filename - The filename of the media item.
 * @param {string} ext - The file extension of the media item.
 */
export interface MediaData {
  key: string
  hash: string
  camera_name: string
  day_obs: string
  channel_name: string
  filename: string
  ext: string
}

/**
 * @extends {MediaData}
 * @description Represents an exposure event, which is a specific instance of media data.
 * @param {string} seq_num - The sequence number of the exposure event.
 */
export interface ExposureEvent extends MediaData {
  seq_num: string
}

/**
 * @description Represents a processing location with its name, title, and associated cameras.
 * @param {string} name - The name of the processing location.
 * @param {string} title - The title of the processing location.
 * @param {Camera[]} cameras - An array of cameras associated with the processing location.
 */
export interface ProcessingLocation {
  name: string
  title: string
  cameras: Camera[]
}

/**
 * @description Represents a camera with its name, title, channels, and other metadata.
 * @param {string} name - The name of the camera.
 * @param {string} title - The title of the camera.
 * @param {Channel[]} channels - An array of channels associated with the camera.
 * @param {string} location - The location of the camera.
 * @param {Metadata} [metadata] - Optional metadata associated with the camera.
 * @param {string} [copy_row_template] - Optional template for copying rows.
 * @param {Record<string, string>} [metadata_columns] - Optional metadata columns for the camera.
 * @param {string} [image_viewer_link] - Optional link to an image viewer.
 * @param {Object} [time_since_clock] - Optional object containing a label for time since clock.
 * @param {Array<MosaicSingleView>} [mosaic_view_meta] - Optional metadata for mosaic views.
 * @param {string} [night_report_label] - Optional label for night reports.
 */
export interface Camera {
  name: string
  title: string
  channels: Channel[]
  location: string
  metadata?: Metadata
  copy_row_template?: string
  metadata_columns?: Record<string, string>
  image_viewer_link?: string
  time_since_clock?: { label: string }
  mosaic_view_meta?: Array<MosaicSingleView>
  night_report_label?: string
  extra_buttons?: ExtraButton[]
}

/**
 * @description Represents a single view configuration in a mosaic display.
 * @param {string} channel - Channel name to display in this mosaic view.
 * @param {string[]} metaColumns - Metadata columns shown for this view.
 * @param {MediaType} mediaType - Media type for the view ("image" or "video").
 * @param {ExposureEvent} [latestEvent] - Optional latest exposure event for the view.
 * @param {boolean} selected - Whether this view is currently selected.
 */
export interface MosaicSingleView {
  channel: string
  metaColumns: string[]
  mediaType: MediaType
  latestEvent?: ExposureEvent
  selected: boolean
}

export type MediaType = "image" | "video"

/**
 * @description Represents a channel with display and configuration properties.
 * @param {string} name - Unique channel identifier.
 * @param {string} title - Human-readable channel title.
 * @param {string} [label] - Optional short label for the channel.
 * @param {string} icon - Icon name or path for the channel.
 * @param {string} colour - Background colour used for the channel display.
 * @param {string} [text_colour] - Optional text colour to use on the channel background.
 * @param {boolean} [per_day] - If true, the channel is displayed per-day instead of per-event.
 */
export interface Channel {
  name: string
  title: string
  label?: string
  icon: string
  colour: string
  text_colour?: string
  per_day?: boolean
}

/**
 * @description Represents a channel data structure mapping day observations
 * to exposure events.
 * TODO: Writing out this structure has identified the amount of
 * redundancy in the data representation. This will be addressed in
 * DM-51895.
 * @example
 * const channelData: ChannelData = {
 *   "1": {
 *     "channel1": {
 *       key: "1",
 *       hash: "abc123",
 *       camera_name: "Camera 1",
 *       day_obs: "2023-01-01",
 *       channel_name: "channel1",
 *       filename: "video1.mp4",
 *       ext: "mp4",
 *       seq_num: "1"
 *     },
 *     "channel2": {
 *       key: "1",
 *       hash: "abc123",
 *       camera_name: "Camera 1",
 *       day_obs: "2023-01-01",
 *       channel_name: "channel2",
 *       filename: "video1.mp4",
 *       ext: "mp4",
 *       seq_num: "1"
 *     }
 *   }
 * };
 */
export interface ChannelData {
  [seqNum: string]: {
    [channelName: string]: ExposureEvent
  }
}

/**
 * @description Represents the structure of a night report containing plots and text data.
 * @param {NightReportPlot[]} [plots] - Optional array of plots for the night report.
 * @param {Record<string, string>} [text] - Optional key-value pairs of text content.
 */
export interface NightReportType {
  plots?: NightReportPlot[]
  text?: Record<string, string>
}

/**
 * @extends {MediaData}
 * @description Represents a plot in a night report with grouping information.
 * @param {string} group - The group category this plot belongs to.
 */
export interface NightReportPlot extends MediaData {
  group: string
}

/**
 * @description Represents calendar data with hierarchical date structure (year > month > day > count).
 * @example
 * const calendarData: CalendarData = {
 *   2023: {
 *     1: {
 *       1: 5,
 *       2: 10
 *     },
 *     2: {
 *       1: 8
 *     }
 *   }
 * };
 */
export interface CalendarData {
  [year: number]: {
    [month: number]: {
      [day: number]: number
    }
  }
}

/**
 * @description Represents navigation data with previous and next exposure events.
 * @param {ExposureEvent | null} prev - The previous exposure event or null if none exists.
 * @param {ExposureEvent | null} next - The next exposure event or null if none exists.
 */
export interface PrevNextType {
  prev: ExposureEvent | null
  next: ExposureEvent | null
}

/**
 * @description Represents contextual values available to RubinTV components.
 * @param {string} siteLocation - Short identifier for the site location.
 * @param {string} locationName - Human-readable location name.
 * @param {Camera} camera - Current camera configuration.
 * @param {string} dayObs - The observation day (yyyy-mm-dd) in context.
 */
export interface RubinTVContextType {
  siteLocation: string
  locationName: string
  camera: Camera
  dayObs: string
}

type SortingDirection = "asc" | "desc"
/**
 * @description Represents sorting configuration for table columns.
 * @param {string} column - The column name to sort by.
 * @param {sortingDirection} order - The sort order, either ascending or descending.
 */
export interface SortingOptions {
  column: string
  order: SortingDirection
}

/**
 * @description Represents filtering configuration for table columns.
 * @param {string} column - The column name to filter by.
 * @param {string | number | boolean} value - The filter value to match against.
 */
export interface FilterOptions {
  column: string
  value: string | number | boolean
}

/**
 * @description Represents a detector identifier with name and key.
 * @param {string} name - The display name of the detector.
 * @param {string} key - The unique key identifier for the detector.
 */
export interface DetectorKey {
  name: string
  key: string
}

/**
 * @description Represents a mapping of detector positions with corner coordinates.
 * @example
 * const detectorMap: DetectorMap = {
 *   "23": {
 *     corners: {
 *       lowerLeft: [0, 0],
 *       lowerRight: [10, 0],
 *       upperRight: [10, 10],
 *       upperLeft: [0, 10]
 *     }
 *   }
 * };
 */
export interface DetectorMap {
  [key: string]: {
    corners: {
      lowerLeft: number[]
      lowerRight: number[]
      upperRight: number[]
      upperLeft: number[]
    }
  }
}

// TODO: Properly constrain the keys of the WorkerStatus and WorkerGroup interfaces
// See https://www.typescriptlang.org/docs/handbook/2/objects.html#literal-types
// and DM-52440

/**
 * @description Represents the status of a single worker process.
 * @param {string} status - The current status of the worker.
 * @param {number} [queue_length] - Optional length of the worker's processing queue.
 */
export interface WorkerStatus {
  status: string
  queue_length?: number
}

/**
 * @description Represents a group of workers with their collective status information.
 * @param {Object} [workers] - Optional mapping of worker IDs to their status.
 * @param {number} [numWorkers] - Optional total number of workers in the group.
 * @param {Record<string, string>} [text] - Optional additional text information about the group.
 */
export interface WorkerGroup {
  workers?: { [workerId: string]: WorkerStatus }
  numWorkers?: number
  text?: Record<string, string>
}

/**
 * @description Represents a collection of worker groups organized by group names.
 * @example
 * const statusSet: StatusSet = {
 *   "group1": {
 *     workers: {
 *       "worker1": { status: "free" },
 *       "worker2": { status: "busy", queue_length: 5 }
 *     },
 *     numWorkers: 2,
 *   },
 *   "group2": {
 *     workers: {
 *       "worker3": { status: "queued", queue_length: 3 }
 *     },
 *   }
 * };
 */
export interface StatusSet {
  [key: string]: WorkerGroup
}

/**
 * @description Represents a Redis endpoint configuration.
 * @param {string} url - The URL of the Redis endpoint.
 * @param {boolean} admin - Whether this endpoint has admin privileges.
 */
export interface RedisEndpoint {
  url: string
  admin: boolean
}

/**
 * @description Props for the top-level table application component.
 * @param {Camera} camera - Camera configuration for the table app.
 * @param {string} locationName - Human readable location name.
 * @param {string} initialDate - Initial date (yyyy-mm-dd) to display.
 * @param {boolean} isHistorical - Whether the view is historical.
 * @param {string} siteLocation - Short site identifier (e.g. 'summit').
 * @param {boolean} isStale - Whether the data is stale.
 */
export interface TableAppProps {
  camera: Camera
  locationName: string
  initialDate: string
  isHistorical: boolean
  siteLocation: string
  isStale: boolean
  seqNum?: number
}

/**
 * @description Props for the row of controls shown above the metadata table.
 * @param {Camera} camera - Camera configuration.
 * @param {string[]} availableColumns - List of available columns to display.
 * @param {string[]} selected - List of currently selected columns.
 * @param {function} setSelected - Callback to update the selected columns.
 * @param {string} date - Current date string.
 * @param {Metadata} metadata - Metadata for the current view.
 * @param {boolean} isHistorical - Whether the view is historical.
 */
export interface AboveTableRowProps {
  camera: Camera
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
  date: string
  metadata: Metadata
  isHistorical: boolean
}

/**
 * @description Props for the component that controls table column visibility.
 * @param {string} cameraName - Name of the camera.
 * @param {string[]} availableColumns - List of available columns to display.
 * @param {string[]} selected - List of currently selected columns.
 * @param {function} setSelected - Callback to update the selected columns.
 */
export interface TableControlProps {
  cameraName: string
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
}

/**
 * @description Props for the button that downloads metadata for a date/camera.
 * @param {string} date - The date for which to download metadata.
 * @param {string} cameraName - The name of the camera.
 * @param {Metadata | null} metadata - The metadata to download.
 */
export interface DownloadMetadataButtonProps {
  date: string
  cameraName: string
  metadata: Metadata | null
}

/**
 * @description Props for the table filter dialog component.
 * @param {string} column - Column name being filtered.
 * @param {(filter: FilterOptions) => void} setFilterOn - Callback to apply a filter.
 * @param {FilterOptions} filterOn - Current filter settings.
 * @param {number} filteredRowsCount - Count of rows after filtering.
 * @param {number} unfilteredRowsCount - Count of rows before filtering.
 */
export interface TableFilterDialogProps {
  column: string
  setFilterOn: (filter: FilterOptions) => void
  filterOn: FilterOptions
  filteredRowsCount: number
  unfilteredRowsCount: number
}

/**
 * @description Props for a table cell showing a channel's event.
 * @param {ExposureEvent | undefined} event - The exposure event to show.
 * @param {string} chanName - Channel name.
 * @param {string} chanColour - Colour used for the channel button.
 * @param {string} [noEventReplacement] - Replacement text when no event exists.
 */
export interface TableChannelCellProps {
  event?: ExposureEvent
  chanName: string
  chanColour: string
  noEventReplacement?: string
}

/**
 * @description Props for a metadata cell in the table.
 * @param {MetadatumType} data - The metadata value for the cell.
 * @param {string} indicator - Indicator string (a column name prefixed with
 * an underscore).
 * @param {string} seqNum - Sequence number for the row.
 * @param {string} columnName - Metadata column name.
 */
export interface TableMetadataCellProps {
  data: MetadatumType
  indicator: string
  seqNum: string
  columnName: string
}

/**
 * @description Props for a single data row in the metadata table.
 * @param {string} seqNum - Sequence number for the row.
 * @param {Camera} camera - Camera configuration for the row.
 * @param {Channel[]} channels - Channels displayed in the row.
 * @param {Record<string, ExposureEvent>} channelRow - Channel->event mapping for this row.
 * @param {MetadataColumn[]} metadataColumns - Ordered metadata columns to render.
 * @param {MetadataRow} metadataRow - Row-specific metadata.
 */
export interface TableRowProps {
  seqNum: string
  camera: Camera
  channels: Channel[]
  channelRow: Record<string, ExposureEvent>
  metadataColumns: MetadataColumn[]
  metadataRow: MetadataRow
  highlightRow?: boolean
}

/**
 * @description Props for the table body component that renders many rows.
 * @param {Camera} camera - Camera configuration.
 * @param {Channel[]} channels - List of channels to render.
 * @param {ChannelData} channelData - Mapping of seq numbers to channel events.
 * @param {MetadataColumn[]} metadataColumns - Metadata columns to include.
 * @param {Metadata} metadata - Metadata mapping for rows.
 * @param {SortingOptions} sortOn - Current sorting options.
 */
export interface TableBodyProps {
  camera: Camera
  channels: Channel[]
  channelData: ChannelData
  metadataColumns: MetadataColumn[]
  metadata: Metadata
  sortOn: SortingOptions
  seqNumToShow?: number
}

/**
 * @description Internal props grouping used for table header sorting/filtering controls.
 * @param {number} filteredRowsCount - Count of rows after filtering.
 * @param {number} unfilteredRowsCount - Count of rows before filtering.
 * @param {SortingOptions} sortOn - Current sorting options.
 * @param {function} setSortOn - Callback to update the sorting options.
 * @param {FilterOptions} filterOn - Current filter settings.
 * @param {function} setFilterOn - Callback to update the filter settings.
 */
interface TableSortingFiltering {
  filteredRowsCount: number
  unfilteredRowsCount: number
  sortOn: SortingOptions
  setSortOn: React.Dispatch<React.SetStateAction<SortingOptions>>
  filterOn: FilterOptions
  setFilterOn: (filter: FilterOptions) => void
}

/**
 * @description Props for a channel header cell in the table (used for both channel and metadata columns).
 * @param {Channel | MetadataColumn} channel - Channel or metadata column being rendered in the header.
 */
export interface TableChannelHeaderProps extends TableSortingFiltering {
  channel: Channel | MetadataColumn
}

/**
 * @description Represents a configurable extra/action button.
 * @param {string} name - Internal button name.
 * @param {string} title - Visible title for the button.
 * @param {string} linkURL - URL opened by the button.
 * @param {string} logo - Logo or icon resource for the button.
 * @param {string} [text_colour] - Optional text colour for the button label.
 * @param {boolean} [text_shadow] - Optional flag to render a text shadow.
 */
export interface ExtraButton {
  name: string
  title: string
  linkURL: string
  logo: string
  text_colour?: string
  text_shadow?: boolean
}

/**
 * @description Represents a per-day event entry (used in per-day listings).
 * @param {string} filename - Filename of the event (used to construct links).
 */
interface PerDayEvent {
  filename: string
}

/**
 * @description Props for the table header including sorting and filtering controls.
 * @param {Camera} camera - Camera configuration for the header.
 * @param {MetadataColumn[]} metadataColumns - Metadata columns to render as headers.
 */
export interface TableHeaderProps extends TableSortingFiltering {
  camera: Camera
  metadataColumns: MetadataColumn[]
}

/**
 * @description Props for the main table view component.
 * @param {Camera} camera - Current camera configuration.
 * @param {ChannelData} channelData - Event data grouped by seq number and channel.
 * @param {Metadata} metadata - Metadata indexed by seq number.
 * @param {MetadataColumn[]} metadataColumns - Columns to render in the table.
 * @param {FilterOptions} filterOn - Active filter options.
 * @param {number} filteredRowsCount - Number of rows after filtering.
 * @param {SortingOptions} sortOn - Current sorting options.
 * @param {string} siteLocation - Short site identifier.
 */
export interface TableViewProps {
  camera: Camera
  channelData: ChannelData
  metadata: Metadata
  metadataColumns: MetadataColumn[]
  filterOn: FilterOptions
  filteredRowsCount: number
  sortOn: SortingOptions
  siteLocation: string
  seqNumToShow?: number
}

/**
 * @description Props for a foldout cell that displays metadata details for a row/column.
 * @param {string} seqNum - Sequence number for the row.
 * @param {string} columnName - Column name for which the foldout shows details.
 * @param {MetadatumType} data - The underlying metadata value for the foldout.
 */
export interface TableFoldoutCellProps {
  seqNum: string
  columnName: string
  data: MetadatumType
}

/**
 * @description Props for a generic button component used across the UI.
 * @param {string} clsName - CSS class name(s) for the button.
 * @param {string} url - Target URL for the button.
 * @param {string} [bckCol] - Optional background colour.
 * @param {string} [iconUrl] - Optional icon URL.
 * @param {string} [logoURL] - Optional logo URL.
 * @param {string} label - Visible label for the button.
 * @param {string} [date] - Optional date associated with the button.
 * @param {string} [textColour] - Optional text colour override.
 * @param {boolean} [textShadow] - Optional flag to enable text shadow.
 */
export interface ButtonProps {
  clsName: string
  url: string
  bckCol?: string
  iconUrl?: string
  logoURL?: string
  label: string
  date?: string
  textColour?: string
  textShadow?: boolean
}

/**
 * @description Represents the props for the AllSky component.
 * @param {string} initialDate - The initial date for the AllSky component.
 * @param {boolean} [isHistorical] - Whether the data is historical.
 * @param {string} locationName - The name of the location.
 * @param {Camera} camera - The camera configuration.
 * @param {CalendarData} [calendar] - The calendar data.
 */
export interface AllSkyProps {
  initialDate: string
  isHistorical?: boolean
  locationName: string
  camera: Camera
  calendar?: CalendarData
}

/**
 * @description Props for a per-day channels component that lists events for a date.
 * @param {string} locationName - Location identifier.
 * @param {Camera} camera - Camera configuration.
 * @param {string} date - Date string (yyyy-mm-dd) for per-day listing.
 * @param {Record<string, PerDayEvent>} perDay - Mapping of per-day events.
 * @param {boolean} isHistorical - Whether view is historical.
 */
export interface PerDayChannelsProps {
  locationName: string
  camera: Camera
  date: string
  perDay: Record<string, PerDayEvent>
  isHistorical: boolean
}

/**
 * @description Props for a component linking to a night report for a given date/camera.
 * @param {string} locationName - Location identifier.
 * @param {Camera} camera - Camera configuration.
 * @param {string} date - Date for the night report.
 * @param {string} nightReportLink - Link template to the night report.
 */
export interface NightReportLinkProps {
  locationName: string
  camera: Camera
  date: string
  nightReportLink: string
}

/**
 * @description Props for a per-day container component (top-level per-day view).
 * @param {string} locationName - Location identifier.
 * @param {Camera} camera - Camera configuration.
 * @param {string} initialDate - Initial date to load.
 * @param {string} initialNRLink - Initial night report link.
 * @param {boolean} isHistorical - Whether the view is historical.
 */
export interface PerDayProps {
  locationName: string
  camera: Camera
  initialDate: string
  initialNRLink: string
  isHistorical: boolean
}

/**
 * @description Props for the media display component that shows a selected exposure.
 * @param {string} locationName - Location identifier.
 * @param {Camera} camera - Camera configuration.
 * @param {ExposureEvent | null} initEvent - Initial event to display (nullable).
 * @param {PrevNextType} prevNext - Prev/next navigation events.
 * @param {string[]} allChannelNames - All channel names for the camera.
 * @param {boolean} isCurrent - Whether the shown media is the current/latest.
 */
export interface MediaDisplayProps {
  locationName: string
  camera: Camera
  initEvent: ExposureEvent | null
  prevNext: PrevNextType
  allChannelNames: string[]
  isCurrent: boolean
}

/**
 * @description Represents an exposure event augmented with explicit media type and source URL.
 * @param {"image" | "video"} mediaType - Whether the bundled media is image or video.
 * @param {string} src - Resolved source URL for the media.
 */
export interface BundledMediaEvent extends ExposureEvent {
  mediaType: "image" | "video"
  src: string
}

/**
 * @description Props for components that render links to other channels for the same event.
 * @param {string[]} allChannelNames - All channel names for the camera.
 * @param {string} thisChannel - Channel currently being viewed.
 * @param {Camera} camera - Camera configuration.
 */
export interface OtherChannelLinksProps {
  allChannelNames: string[]
  thisChannel: string
  camera: Camera
}

/**
 * @description Props for a small component that displays a single media item in AllSky contexts.
 * @param {ExposureEvent | null} details - Event details or null if none.
 * @param {string} locationName - Location identifier.
 */
export interface AllSkyMediaProps {
  details: ExposureEvent | null
  locationName: string
}

/**
 * @description Props for the site banner component.
 * @param {string} [siteLocation] - Short site identifier (optional).
 * @param {string} locationName - Human-readable location name.
 * @param {Camera} camera - Camera configuration.
 */
export interface BannerProps {
  siteLocation?: string
  locationName: string
  camera: Camera
}

/**
 * @description Camera type that guarantees the presence of time_since_clock config.
 * @param {{label: string}} time_since_clock - Object containing the clock label.
 */
export interface CameraWithTimeSinceClock extends Camera {
  time_since_clock: {
    label: string
  }
}

/**
 * @description Props for the component that shows time-since-last-image using camera's clock label.
 * @param {Metadata} metadata - Full metadata mapping for the camera/day.
 * @param {CameraWithTimeSinceClock} camera - Camera which includes a time_since_clock property.
 */
export interface TimeSinceLastImageClockProps {
  metadata: Metadata
  camera: CameraWithTimeSinceClock
}

/**
 * @description Props for the detector canvas visualization.
 * @param {DetectorMap} detectorMap - Map describing detector geometries.
 * @param {WorkerGroup} detectorStatuses - Current statuses for detectors.
 */
export interface DetectorCanvasProps {
  detectorMap: DetectorMap
  detectorStatuses: WorkerGroup
}

/**
 * @description Props for a detector section showing a mapped detector area and statuses.
 * @param {string} title - Title shown for the section.
 * @param {DetectorMap} map - Detector layout map.
 * @param {StatusSet} statuses - Status set for detectors.
 * @param {string} redisKey - Redis key used for this detector section.
 * @param {"small" | "large"} [size] - Optional display size.
 */
export interface DetectorSectionProps {
  title: string
  map: DetectorMap
  statuses: StatusSet
  redisKey: string
  size?: "small" | "large"
}

/**
 * @description Props for a small set of detector status cells.
 * @param {WorkerGroup} statuses - Worker group statuses to render.
 * @param {string} prefix - Prefix used to construct element IDs or keys.
 */
export interface DetectorCellsProps {
  statuses: WorkerGroup
  prefix: string
}

/**
 * @description Props for the detector status visualization which connects to Redis.
 * @param {DetectorKey[]} detectorKeys - List of detector keys to monitor.
 * @param {string} redisEndpointUrl - Endpoint URL for Redis connection.
 * @param {boolean} admin - Whether admin controls are enabled.
 */
export interface DetectorStatusVisualizationProps {
  detectorKeys: DetectorKey[]
  redisEndpointUrl: string
  admin: boolean
}

/**
 * @description Props for the Step1b detector section.
 * @param {string} title - Title for the section.
 * @param {StatusSet["sfmStep1b"]} statuses - Status data specific to step1b set.
 * @param {string} redisKey - Redis key to subscribe to.
 */
export interface Step1bSectionProps {
  title: string
  statuses: StatusSet["sfmStep1b"]
  redisKey: string
}

/**
 * @description Props for a general confirmation modal.
 * @param {string} [title] - Optional modal title.
 * @param {string} [message] - Optional message body.
 * @param {() => void} [onConfirm] - Callback invoked on confirm.
 * @param {() => void} [onCancel] - Callback invoked on cancel.
 */
export interface ConfirmationModalProps {
  title?: string
  message?: string
  onConfirm?: () => void
  onCancel?: () => void
}

/**
 * @description Props for the mosaic view wrapper component.
 * @param {string} locationName - Location identifier for the mosaic view.
 * @param {CameraWithMosaicViewMeta} camera - Camera with mosaic metadata configured.
 */
export interface MosaicViewProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
}

/**
 * @description Camera extension that guarantees mosaic view metadata.
 * @param {MosaicSingleView[]} mosaic_view_meta - List of mosaic view configurations.
 */
export interface CameraWithMosaicViewMeta extends Camera {
  mosaic_view_meta: MosaicSingleView[]
}

/**
 * @description Props for rendering a single channel's media within mosaic view.
 * @param {string} locationName - Location identifier.
 * @param {CameraWithMosaicViewMeta} camera - Camera configuration.
 * @param {ExposureEvent | undefined} event - Specific event for this media cell.
 * @param {MediaType} mediaType - Media type ("image" or "video").
 */
export interface ChannelMediaProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
  event: ExposureEvent | undefined
  mediaType: MediaType
}

/**
 * @description Props for channel metadata presentation used in mosaic views.
 * @param {MosaicSingleView} view - Selected mosaic view configuration.
 * @param {Record<string, Record<string, string>>} metadata - Nested metadata mapping used by the view.
 */
export interface ChannelMetadataProps {
  view: MosaicSingleView
  metadata: Record<string, Record<string, string>>
}

/**
 * @description Props for an item in the channel list view for mosaics.
 * @param {string} locationName - Location identifier.
 * @param {CameraWithMosaicViewMeta} camera - Camera configuration.
 * @param {MosaicSingleView} view - Mosaic view entry represented by this item.
 * @param {Record<string, Record<string, string>>} currentMeta - Current metadata mapping.
 * @param {(view: MosaicSingleView) => void} selectView - Callback to select this view.
 * @param {boolean} isSelectable - Whether the item can be selected.
 */
export interface ChannelListViewItemProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
  view: MosaicSingleView
  currentMeta: Record<string, Record<string, string>>
  selectView: (view: MosaicSingleView) => void
  isSelectable: boolean
}

/**
 * @description Props for the night report top-level component.
 * @param {NightReportType} initialNightReport - Initial night report data.
 * @param {string} initialDate - Date of the night report.
 * @param {Camera} camera - Camera configuration.
 * @param {string} locationName - Location identifier.
 * @param {string} homeUrl - Base URL for links.
 */
export interface NightReportProps {
  initialNightReport: NightReportType
  initialDate: string
  camera: Camera
  locationName: string
  homeUrl: string
}

/**
 * @description Props for the night report tabs control.
 * @param {TabType[]} tabs - Available tabs.
 * @param {string} selected - Currently selected tab id.
 * @param {React.Dispatch<React.SetStateAction<string>>} setSelected - Setter for selected tab.
 */
export interface NightReportTabProps {
  tabs: TabType[]
  selected: string
  setSelected: React.Dispatch<React.SetStateAction<string>>
}

/**
 * @description Props for rendering a text tab inside the night report.
 * @param {TextTabType | undefined} tab - Tab data (text) to render.
 * @param {string} selected - Currently selected tab id.
 */
export interface NightReportTextProps {
  tab: TextTabType | undefined
  selected: string
}

/**
 * @description Props for rendering a plot tab inside the night report.
 * @param {PlotTabType | undefined} tab - Tab data (plots) to render.
 * @param {string} selected - Currently selected tab id.
 * @param {Camera} camera - Camera context for plot links.
 * @param {string} locationName - Location identifier.
 * @param {string} homeUrl - Base URL for plot links.
 */
export interface NightReportPlotProps {
  tab: PlotTabType | undefined
  selected: string
  camera: Camera
  locationName: string
  homeUrl: string
}

/**
 * Generic base structure for a night report tab.
 *
 * This generic type captures the common shape of tabs used by the NightReport
 * UI: an identifier, a human-visible label, a literal `type` discriminator,
 * and a `data` payload whose shape depends on the tab type.
 *
 * @template T - A literal string union that discriminates the tab kind (e.g. "text" | "plot").
 * @template D - The payload type carried by the tab (e.g. Record<string,string> for text tabs,
 *                or an array of plots for plot tabs).
 *
 * Fields:
 * - id: Unique string identifier for the tab (used for DOM ids and state).
 * - label: Human-readable title shown in the UI.
 * - type: Literal discriminator for runtime/type narrowing.
 * - data: Typed payload associated with the tab.
 */
type BaseTab<T extends string, D> = {
  id: string
  label: string
  type: T
  data: D
}

/**
 * A tab that contains textual content or links.
 *
 * Typical usage:
 * - Efficiency or QA text sections where `data` is a mapping of keys to strings.
 * - Keys prefixed with "text_" indicate multi-line textual blocks.
 *
 * - id: tab identifier (e.g. "efficiency")
 * - label: visible label (e.g. "Efficiency")
 * - type: the literal "text"
 * - data: mapping of titles/keys to string content or URLs
 */
export type TextTabType = BaseTab<"text", Record<string, string>>

/**
 * A tab that contains a collection of plots.
 *
 * Typical usage:
 * - Each plot entry extends MediaData (filename, hash, etc.) and belongs to a group.
 *
 * - id: sanitized group identifier (used for selection)
 * - label: display group name shown in the UI
 * - type: the literal "plot"
 * - data: array of NightReportPlot entries to render as images/figures
 */
export type PlotTabType = BaseTab<"plot", NightReportPlot[]>

/**
 * Discriminated union of all supported tab types for the NightReport UI.
 *
 * This union allows code to narrow on `.type` to safely access the concrete
 * `.data` payload (e.g. when rendering text vs. plots).
 */
export type TabType = TextTabType | PlotTabType

/**
 * @description Props for the calendar component used across RubinTV.
 * @param {string} selectedDate - Currently selected date string (yyyy-mm-dd).
 * @param {CalendarData} initialCalendarData - Initial calendar counts mapping.
 * @param {Camera} camera - Camera configuration.
 * @param {string} locationName - Human-readable location name.
 */
export interface RubinCalendarProps {
  selectedDate: string
  initialCalendarData: CalendarData
  camera: Camera
  locationName: string
}

/**
 * @description Props for a single day cell within the calendar component.
 * @param {number} day - Day of month.
 * @param {string} dateStr - Date string (yyyy-mm-dd).
 * @param {Record<number, number>} calendarData - Day->count mapping for the month.
 * @param {string | null} [dayObs] - Optional observation day identifier.
 * @param {string} selectedDate - Currently selected date string.
 * @param {string} cameraUrl - URL for the camera/day.
 * @param {boolean} [noSeqNum] - If true, sequence numbers are omitted.
 */
export interface CalendarDayProps {
  day: number
  dateStr: string
  calendarData: CalendarData[number][number]
  dayObs?: string | null
  selectedDate: string // formatted as "yyyy-mm-dd"
  cameraUrl: string
  noSeqNum?: boolean
}

/**
 * @description Props for rendering a calendar month.
 * @param {number} year - Calendar year.
 * @param {number} month - Calendar month (1-12).
 * @param {boolean} isSelected - Whether this month is selected.
 * @param {CalendarData} calendarData - Full calendar data mapping.
 * @param {string} cameraUrl - Base camera URL for day links.
 * @param {boolean} noSeqNum - Whether sequence numbers are hidden.
 * @param {Calendar.Calendar} calendarFrame - Calendar frame instance used to build the month.
 * @param {Date} selectedDate - Currently selected date as Date object.
 * @param {string | null} [dayObs] - Optional day_obs for the month.
 */
export interface CalendarMonthProps {
  year: number
  month: number
  isSelected: boolean
  calendarData: CalendarData
  cameraUrl: string
  noSeqNum: boolean
  calendarFrame: Calendar.Calendar
  selectedDate: Date
  dayObs?: string | null
}

/**
 * @description Props for rendering a calendar year and its months.
 * @param {number} year - The year being rendered.
 * @param {number} yearToDisplay - The display year (for multi-year displays).
 * @param {Date} selectedDate - Currently selected date as Date object.
 * @param {CalendarData} calendarData - Full calendar data mapping.
 * @param {Calendar.Calendar} calendarFrame - Calendar frame instance used to build months.
 * @param {string} cameraUrl - Base camera URL for links.
 * @param {boolean} noSeqNum - Whether sequence numbers are hidden.
 * @param {string | null} [dayObs] - Optional day_obs for the year.
 */
export interface CalendarYearProps {
  year: number
  yearToDisplay: number
  selectedDate: Date
  calendarData: CalendarData
  calendarFrame: Calendar.Calendar
  cameraUrl: string
  noSeqNum: boolean
  dayObs?: string | null
}

/**
 * @description Context type for managing modal content in the application.
 * @param {React.ReactNode | null} modalContent - Current modal content or null if none.
 * @param {(content: React.ReactNode | null) => void} setModalContent - Function to update modal content.
 */
export interface ModalContextType {
  modalContent: React.ReactNode | null
  setModalContent: (content: React.ReactNode | null) => void
}
