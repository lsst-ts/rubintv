import React from "react"
import { createRoot } from "react-dom/client"
import AllSky from "../components/AllSky"
import { WebsocketClient } from "../modules/ws-service-client"
import { _getById } from "../modules/utils"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }
  const { locationName, camera, date, calendar, isHistorical } = window.APP_DATA

  const ws = new WebsocketClient()
  if (!isHistorical) {
    ws.subscribe("camera", locationName, camera.name, null)
  } else {
    ws.subscribe("calendar", locationName, camera.name, null)
  }

  const allsky = _getById("allsky")
  if (!allsky) {
    console.error("AllSky element not found")
    return
  }
  const allSkyRoot = createRoot(allsky)
  allSkyRoot.render(
    <AllSky
      initialDate={date}
      isHistorical={isHistorical}
      locationName={locationName}
      camera={camera}
      calendar={calendar}
    />
  )
})()
