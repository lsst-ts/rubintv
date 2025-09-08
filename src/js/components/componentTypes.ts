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
  seq_num: string
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
 * @property {Array<MosaicSingleView>} [mosaic_view_meta] - Optional metadata for mosaic views.
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
  mosaic_view_meta?: Array<MosaicSingleView>
  night_report_label?: string
  extra_buttons?: ExtraButton[]
}

export interface MosaicSingleView {
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

type SortingDirection = "asc" | "desc"
/**
 * @description Represents sorting configuration for table columns.
 * @property {string} column - The column name to sort by.
 * @property {sortingDirection} order - The sort order, either ascending or descending.
 */
export interface SortingOptions {
  column: string
  order: SortingDirection
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
 * @property {string} url - The URL of the Redis endpoint.
 * @property {boolean} admin - Whether this endpoint has admin privileges.
 */
export interface RedisEndpoint {
  url: string
  admin: boolean
}

export interface TableAppProps {
  camera: Camera
  locationName: string
  initialDate: string
  isHistorical: boolean
  siteLocation: string
  isStale: boolean
}

export interface AboveTableRowProps {
  camera: Camera
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
  date: string
  metadata: Metadata
  isHistorical: boolean
}

export interface TableControlProps {
  cameraName: string
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
}

export interface DownloadMetadataButtonProps {
  date: string
  cameraName: string
  metadata: Metadata | null
}

export interface TableFilterDialogProps {
  column: string
  setFilterOn: (filter: FilterOptions) => void
  filterOn: FilterOptions
  filteredRowsCount: number
  unfilteredRowsCount: number
}

export interface TableChannelCellProps {
  event?: ExposureEvent
  chanName: string
  chanColour: string
  noEventReplacement?: string
}

export interface TableMetadataCellProps {
  data: MetadatumType
  indicator: string
  seqNum: string
  columnName: string
}

export interface TableRowProps {
  seqNum: string
  camera: Camera
  channels: Channel[]
  channelRow: Record<string, ExposureEvent>
  metadataColumns: MetadataColumn[]
  metadataRow: MetadataRow
}

export interface TableBodyProps {
  camera: Camera
  channels: Channel[]
  channelData: ChannelData
  metadataColumns: MetadataColumn[]
  metadata: Metadata
  sortOn: SortingOptions
}

interface TableSortingFiltering {
  filteredRowsCount: number
  unfilteredRowsCount: number
  sortOn: SortingOptions
  setSortOn: React.Dispatch<React.SetStateAction<SortingOptions>>
  filterOn: FilterOptions
  setFilterOn: (filter: FilterOptions) => void
}

export interface TableChannelHeaderProps extends TableSortingFiltering {
  channel: Channel | MetadataColumn
}

export interface TableHeaderProps extends TableSortingFiltering {
  camera: Camera
  metadataColumns: MetadataColumn[]
}

export interface TableViewProps {
  camera: Camera
  channelData: ChannelData
  metadata: Metadata
  metadataColumns: MetadataColumn[]
  filterOn: FilterOptions
  filteredRowsCount: number
  sortOn: SortingOptions
  siteLocation: string
}

export interface TableFoldoutCellProps {
  seqNum: string
  columnName: string
  data: MetadatumType
}

export interface ExtraButton {
  name: string
  title: string
  linkURL: string
  logo: string
  text_colour?: string
  text_shadow?: boolean
}

export interface PerDayEvent {
  filename: string
}

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

export interface PerDayChannelsProps {
  locationName: string
  camera: Camera
  date: string
  perDay: Record<string, PerDayEvent>
  isHistorical: boolean
}

export interface NightReportLinkProps {
  locationName: string
  camera: Camera
  date: string
  nightReportLink: string
}

export interface PerDayProps {
  locationName: string
  camera: Camera
  initialDate: string
  initialNRLink: string
  isHistorical: boolean
}

/**
 * @description Represents the props for the AllSky component.
 * @property {string} initialDate - The initial date for the AllSky component.
 * @property {boolean} [isHistorical] - Whether the data is historical.
 * @property {string} locationName - The name of the location.
 * @property {Camera} camera - The camera configuration.
 * @property {CalendarData} [calendar] - The calendar data.
 */
export interface AllSkyProps {
  initialDate: string
  isHistorical?: boolean
  locationName: string
  camera: Camera
  calendar?: CalendarData
}

export interface MediaDisplayProps {
  locationName: string
  camera: Camera
  initEvent: ExposureEvent | null
  prevNext: PrevNextType
  allChannelNames: string[]
  isCurrent: boolean
}

export interface BundledMediaEvent extends ExposureEvent {
  mediaType: "image" | "video"
  src: string
}

export interface OtherChannelLinksProps {
  allChannelNames: string[]
  thisChannel: string
  camera: Camera
}

export interface AllSkyMediaProps {
  details: ExposureEvent | null
  locationName: string
}

export interface BannerProps {
  siteLocation?: string
  locationName: string
  camera: Camera
}

export interface CameraWithTimeSinceClock extends Camera {
  time_since_clock: {
    label: string
  }
}

export interface TimeSinceLastImageClockProps {
  metadata: Metadata
  camera: CameraWithTimeSinceClock
}

export interface DetectorCanvasProps {
  detectorMap: DetectorMap
  detectorStatuses: WorkerGroup
}

export interface DetectorSectionProps {
  title: string
  map: DetectorMap
  statuses: StatusSet
  redisKey: string
  size?: "small" | "large"
}

export interface DetectorCellsProps {
  statuses: WorkerGroup
  prefix: string
}

export interface DetectorStatusVisualizationProps {
  detectorKeys: DetectorKey[]
  redisEndpointUrl: string
  admin: boolean
}

export interface Step1bSectionProps {
  title: string
  statuses: StatusSet["sfmStep1b"]
  redisKey: string
}

export interface ConfirmationModalProps {
  title?: string
  message?: string
  onConfirm?: () => void
  onCancel?: () => void
}

export interface MosaicViewProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
}

export interface CameraWithMosaicViewMeta extends Camera {
  mosaic_view_meta: MosaicSingleView[]
}

export interface ChannelMediaProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
  event: ExposureEvent | undefined
  mediaType: MediaType
}

export interface ChannelMetadataProps {
  view: MosaicSingleView
  metadata: Record<string, Record<string, string>>
}

export interface ChannelListViewItemProps {
  locationName: string
  camera: CameraWithMosaicViewMeta
  view: MosaicSingleView
  currentMeta: Record<string, Record<string, string>>
  selectView: (view: MosaicSingleView) => void
  isSelectable: boolean
}

export interface NightReportProps {
  initialNightReport: NightReportType
  initialDate: string
  camera: Camera
  locationName: string
  homeUrl: string
}

export interface NightReportTabProps {
  tabs: TabType[]
  selected: string
  setSelected: React.Dispatch<React.SetStateAction<string>>
}

export interface NightReportTextProps {
  tab: TextTabType | undefined
  selected: string
}

export interface NightReportPlotProps {
  tab: PlotTabType | undefined
  selected: string
  camera: Camera
  locationName: string
  homeUrl: string
}

type BaseTab<T extends string, D> = {
  id: string
  label: string
  type: T
  data: D
}

export type TextTabType = BaseTab<"text", Record<string, string>>
export type PlotTabType = BaseTab<"plot", NightReportPlot[]>
export type TabType = TextTabType | PlotTabType

export interface RubinCalendarProps {
  selectedDate: string
  initialCalendarData: CalendarData
  camera: Camera
  locationName: string
}

export interface CalendarDayProps {
  day: number
  dateStr: string
  calendarData: CalendarData[number][number]
  dayObs?: string | null
  selectedDate: string // formatted as "yyyy-mm-dd"
  cameraUrl: string
  noSeqNum?: boolean
}

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
