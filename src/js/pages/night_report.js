import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
import NightReport from "../components/NightReport"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }

  const {
    locationName,
    camera = {},
    nightReport = {},
    date = "",
    homeUrl = "",
    isHistorical,
  } = window.APP_DATA

  if (!isHistorical) {
    // eslint-disable-next-line no-unused-vars
    const ws = new WebsocketClient()
    ws.subscribe("service", "nightreport", locationName, camera.name)
  }
  const tableRoot = createRoot(_getById("night-report"))
  tableRoot.render(
    <NightReport
      initialNightReport={nightReport}
      camera={camera}
      locationName={locationName}
      initialDate={date}
      homeUrl={homeUrl}
    />
  )
})()
