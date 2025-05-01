import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import Detector from "../components/Detector"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  const { locationName, camera = {}, date = "", isHistorical } = window.APP_DATA

  // Set up websocket connection if not historical
  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "detectors")
  }

  const tableRoot = createRoot(_getById("detectors"))
  tableRoot.render(<Detector />)
})()
