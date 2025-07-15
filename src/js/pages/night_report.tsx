import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
import NightReport from "../components/NightReport"
import { Camera, NightReportType } from "js/components/componentTypes"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }

  const {
    locationName,
    camera = {} as Camera,
    nightReport = {} as NightReportType,
    date = "",
    homeUrl = "",
    isHistorical,
  } = window.APP_DATA

  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("nightreport", locationName, camera.name)
  }
  const nightReportElement = _getById("night-report")
  if (!nightReportElement) {
    console.error("Night report element not found")
    return
  }
  const tableRoot = createRoot(nightReportElement)
  tableRoot.render(
    <NightReport
      initialNightReport={nightReport}
      camera={camera as Camera}
      locationName={locationName}
      initialDate={date}
      homeUrl={homeUrl}
    />
  )
})()
