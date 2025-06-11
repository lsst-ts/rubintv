/** A single item of metadata is either a string, number or nested object of
 * key-value pairs. In the case of the latter, if one of the keys is
 * 'DISPLAY_VALUE', it's value is a UTF-8 encoded character to display as an
 * icon in a button in the table */
type MetadatumType =
  | string
  | number
  | boolean
  | { DISPLAY_VALUE?: string; [key: string]: any }
  | any[]

export interface Metadatum {
  [key: string]: MetadatumType
}

export interface Metadata {
  [key: string]: Metadatum
}

/** An ExposureEvent takes the shape:
 * {
    key: <reference for object in S3 bucket>
    hash: <hash of object given by S3>
    camera_name: <name of associated camera>
    day_obs: <date of event in format 'YYYY-MM-DD'>
    channel_name: <name of associated channel>
    seq_num: <sequence number of event>
    filename: <filename of the event>
    ext: <file extension>
  } */
export interface ExposureEvent {
  key: string
  hash: string
  camera_name: string
  day_obs: string
  channel_name: string
  seq_num: number | string
  filename: string
  ext: string
}

export interface Camera {
  name: string
  title: string
  channels: Channel[]
  location: string
  metadata?: Metadata
  time_since_clock?: { label: string }
}

export interface Channel {
  name: string
  label?: string
  title: string
  icon: string
  colour: string
}

export interface ChannelData {
  [key: string]: ExposureEvent[]
}

export interface NightReportData {
  key: string
  hash: string
  camera: string
  day_obs: string
  group: string
  filename: string
  ext: string
}

export interface MosiacSingleView {
  channel: string
  metaColumns: string[]
  latestImage: string
  latestMetadata: Metadata
}

export interface CalendarData {
  [key: number]: {
    [key: number]: {
      [key: number]: number
    }
  }
}
