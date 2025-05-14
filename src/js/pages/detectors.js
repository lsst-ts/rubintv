import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import Detector from "../components/Detector"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  const { isHistorical, detectorKeys, homeUrl } = window.APP_DATA

  const redisEndpointUrl = new URL("api/redis", homeUrl).toString()

  // Set up websocket connection if not historical
  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "detectors")
  }

  const tableRoot = createRoot(_getById("detectors"))
  tableRoot.render(
    <Detector detectorKeys={detectorKeys} redisEndpointUrl={redisEndpointUrl} />
  )
})()
