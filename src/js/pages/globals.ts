import { AdminInfo } from "../components/AdminPanels"
import {
  Camera,
  Channel,
  CalendarData,
  DetectorKey,
  NightReportType,
  PrevNextType,
  ExposureEvent,
} from "js/components/componentTypes"

export {}

declare global {
  interface Window {
    APP_DATA: {
      historicalBusy: boolean
      admin: AdminInfo
      homeUrl: string
      baseUrl: string
      locationName: string
      camera: Camera
      date: string
      calendar: CalendarData
      isHistorical: boolean
      nightReportLink: string
      siteLocation: string
      detectorKeys: DetectorKey[]
      nightReport: NightReportType
      isCurrent: boolean
      prevNext: PrevNextType
      channel: Channel
      event: ExposureEvent | null
      allChannelNames: string[]
    }
  }
}
