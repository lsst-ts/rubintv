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

export interface MetadataRow {
  [key: string]: MetadatumType
}

export interface Metadata {
  [key: string]: MetadataRow
}

export interface MetadataColumn {
  name: string
  desc: string
}

export interface MediaData {
  key: string
  hash: string
  camera_name: string
  day_obs: string
  channel_name: string
  filename: string
  ext: string
}

export interface ExposureEvent extends MediaData {
  seq_num: number | string
}

export interface ProcessingLocation {
  name: string
  title: string
  cameras: Camera[]
}

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

export interface ChannelData {
  [key: string]: {
    [key: string]: ExposureEvent
  }
}

export interface NightReportType {
  plots?: NightReportPlot[]
  text?: Record<string, string>
}

export interface NightReportPlot extends MediaData {
  group: string
}

export interface CalendarData {
  [key: number]: {
    [key: number]: {
      [key: number]: number
    }
  }
}

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

export interface SortingOptions {
  column: string
  order: "asc" | "desc"
}

export interface FilterOptions {
  column: string
  value: string | number | boolean
}

export interface DetectorKey {
  name: string
  key: string
}

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

export interface WorkerStatus {
  status: string
  queue_length?: number
}

export interface WorkerGroup {
  workers?: { [workerId: string]: WorkerStatus }
  numWorkers?: number
  text?: Record<string, string>
}

export interface StatusSet {
  [key: string]: WorkerGroup
}

export interface RedisEndpoint {
  url: string
  admin: boolean
}

export const RedisEndpointContext = createContext<RedisEndpoint | null>(null)
