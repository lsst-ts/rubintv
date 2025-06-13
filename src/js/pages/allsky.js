import React from "react"
import { createRoot } from "react-dom/client"
import AllSky from "../components/AllSky"
import { WebsocketClient } from "../modules/ws-service-client.js"
import { _getById } from "../modules/utils"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }
  const { locationName, camera, date, calendar, isHistorical } = window.APP_DATA

  const ws = new WebsocketClient()
  if (!isHistorical) {
    ws.subscribe("service", "camera", locationName, camera.name)
  } else {
    ws.subscribe("service", "calendar", locationName, camera.name)
  }

  const allSkyRoot = createRoot(_getById("allsky"))
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
