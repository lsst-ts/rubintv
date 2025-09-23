import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import Detector from "../components/Detector"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  const { isHistorical, detectorKeys, homeUrl, admin } = window.APP_DATA

  const redisEndpointUrl = new URL("api/redis", homeUrl).toString()

  // Set up websocket connection if not historical
  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("detectors")
  }

  const detectorsElement = _getById("detectors")
  if (!detectorsElement) {
    console.error("Detectors element not found")
    return
  }
  const tableRoot = createRoot(detectorsElement)
  tableRoot.render(
    <Detector
      detectorKeys={detectorKeys}
      redisEndpointUrl={redisEndpointUrl}
      admin={admin !== null}
    />
  )
})()
