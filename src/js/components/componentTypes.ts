import { createContext } from "react"
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
 * @property {string} [key] - The key for the metadata item.
 * @property {MetadatumType} value - The value of the metadata item, which
 * can be a string, number, boolean, or an object with string keys and values.
 */
export interface MetadataRow {
  [key: string]: MetadatumType
}

/**
 * @description Represents a collection of metadata rows.
 * @property {string} [seqNum] - The key for the metadata item.
 * @property {MetadataRow} value - The value of the metadata item, which
 * is an object containing key-value pairs of metadata.
 */
export interface Metadata {
  [seqNum: string]: MetadataRow
}

/**
 * @description Represents a column in a metadata table.
 * @property {string} name - The name of the column.
 * @property {string} [desc] - An optional description of the column.
 */
export interface MetadataColumn {
  name: string
  desc?: string
}

/**
 * @description Represents a single media item.
 * @property {string} key - A unique identifier for the media item in the bucket.
 * @property {string} hash - A hash value for the media item.
 * @property {string} camera_name - The name of the camera that captured the media.
 * @property {string} day_obs - The observation day of the media item.
 * @property {string} channel_name - The name of the channel associated with the media.
 * @property {string} filename - The filename of the media item.
 * @property {string} ext - The file extension of the media item.
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
 * @property {string} seq_num - The sequence number of the exposure event.
 */
export interface ExposureEvent extends MediaData {
  seq_num: number | string
}

/**
 * @description Represents a processing location with its name, title, and associated cameras.
 * @property {string} name - The name of the processing location.
 * @property {string} title - The title of the processing location.
 * @property {Camera[]} cameras - An array of cameras associated with the processing location.
 */
export interface ProcessingLocation {
  name: string
  title: string
  cameras: Camera[]
}

/**
 * @description Represents a camera with its name, title, channels, and other metadata.
 * @property {string} name - The name of the camera.
 * @property {string} title - The title of the camera.
 * @property {Channel[]} channels - An array of channels associated with the camera.
 * @property {string} location - The location of the camera.
 * @property {Metadata} [metadata] - Optional metadata associated with the camera.
 * @property {string} [copy_row_template] - Optional template for copying rows.
 * @property {Record<string, string>} [metadata_columns] - Optional metadata columns for the camera.
 * @property {string} [image_viewer_link] - Optional link to an image viewer.
 * @property {Object} [time_since_clock] - Optional object containing a label for time since clock.
 * @property {Array<MosiacSingleView>} [mosaic_view_meta] - Optional metadata for mosaic views.
 * @property {string} [night_report_label] - Optional label for night reports.
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
  mosaic_view_meta?: Array<MosiacSingleView>
  night_report_label?: string
}

export interface MosiacSingleView {
  channel: string
  metaColumns: string[]
  mediaType: MediaType
  latestEvent?: ExposureEvent
  selected: boolean
}

export type MediaType = "image" | "video"

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
 * @description Represents a channel data structure mapping day observations to exposure events.
 * @property {Object} [key] - Dynamic key representing a day observation.
 * @property {Object} value - Nested object mapping sequence numbers to exposure events.
 */
export interface ChannelData {
  [key: string]: {
    [key: string]: ExposureEvent
  }
}

/**
 * @description Represents the structure of a night report containing plots and text data.
 * @property {NightReportPlot[]} [plots] - Optional array of plots for the night report.
 * @property {Record<string, string>} [text] - Optional key-value pairs of text content.
 */
export interface NightReportType {
  plots?: NightReportPlot[]
  text?: Record<string, string>
}

/**
 * @extends {MediaData}
 * @description Represents a plot in a night report with grouping information.
 * @property {string} group - The group category this plot belongs to.
 */
export interface NightReportPlot extends MediaData {
  group: string
}

/**
 * @description Represents calendar data with hierarchical date structure (year > month > day > count).
 * @property {Object} [key] - Year as numeric key.
 * @property {Object} value - Nested object with month as key.
 * @property {Object} value.value - Nested object with day as key.
 * @property {number} value.value.value - Count value for the specific date.
 */
export interface CalendarData {
  [key: number]: {
    [key: number]: {
      [key: number]: number
    }
  }
}

/**
 * @description Represents navigation data with previous and next exposure events.
 * @property {ExposureEvent | null} prev - The previous exposure event or null if none exists.
 * @property {ExposureEvent | null} next - The next exposure event or null if none exists.
 */
export interface PrevNextType {
  prev: ExposureEvent | null
  next: ExposureEvent | null
}

export interface RubinTVContextType {
  siteLocation: string
  locationName: string
  camera: Camera
  dayObs: string
}

export const RubinTVTableContext = createContext<
  RubinTVContextType | undefined
>(undefined)

/**
 * @description Represents sorting configuration for table columns.
 * @property {string} column - The column name to sort by.
 * @property {"asc" | "desc"} order - The sort order, either ascending or descending.
 */
export interface SortingOptions {
  column: string
  order: "asc" | "desc"
}

/**
 * @description Represents filtering configuration for table columns.
 * @property {string} column - The column name to filter by.
 * @property {string | number | boolean} value - The filter value to match against.
 */
export interface FilterOptions {
  column: string
  value: string | number | boolean
}

/**
 * @description Represents a detector identifier with name and key.
 * @property {string} name - The display name of the detector.
 * @property {string} key - The unique key identifier for the detector.
 */
export interface DetectorKey {
  name: string
  key: string
}

/**
 * @description Represents a mapping of detector positions with corner coordinates.
 * @property {Object} [key] - Dynamic key representing a detector identifier.
 * @property {Object} value - Object containing corner coordinate information.
 * @property {Object} value.corners - Corner coordinates for the detector.
 * @property {number[]} value.corners.lowerLeft - [x, y] coordinates of the lower left corner.
 * @property {number[]} value.corners.lowerRight - [x, y] coordinates of the lower right corner.
 * @property {number[]} value.corners.upperRight - [x, y] coordinates of the upper right corner.
 * @property {number[]} value.corners.upperLeft - [x, y] coordinates of the upper left corner.
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

/**
 * @description Represents the status of a single worker process.
 * @property {string} status - The current status of the worker.
 * @property {number} [queue_length] - Optional length of the worker's processing queue.
 */
export interface WorkerStatus {
  status: string
  queue_length?: number
}

/**
 * @description Represents a group of workers with their collective status information.
 * @property {Object} [workers] - Optional mapping of worker IDs to their status.
 * @property {number} [numWorkers] - Optional total number of workers in the group.
 * @property {Record<string, string>} [text] - Optional additional text information about the group.
 */
export interface WorkerGroup {
  workers?: { [workerId: string]: WorkerStatus }
  numWorkers?: number
  text?: Record<string, string>
}

/**
 * @description Represents a collection of worker groups organized by group names.
 * @property {WorkerGroup} [key] - Dynamic key representing a worker group name.
 */
export interface StatusSet {
  [key: string]: WorkerGroup
}

/**
 * @description Represents a Redis endpoint configuration.
 * @property {string} url - The URL of the Redis endpoint.
 * @property {boolean} admin - Whether this endpoint has admin privileges.
 */
export interface RedisEndpoint {
  url: string
  admin: boolean
}

export const RedisEndpointContext = createContext<RedisEndpoint | null>(null)
