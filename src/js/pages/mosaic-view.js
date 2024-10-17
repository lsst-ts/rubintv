import React from "react"
import { createRoot } from "react-dom/client"
import { WebsocketClient } from "../modules/ws-service-client"
import MosaicView from "../components/MosaicView"
import { _getById } from "../modules/utils"

;(function () {
  const locationName = window.APP_DATA.locationName || ""
  const camera = window.APP_DATA.camera || {}
  const ws = new WebsocketClient()
  ws.subscribe("historicalStatus")

  let hasSequencedChannels = null
  camera.mosaic_view_meta.forEach((view) => {
    ws.subscribe("service", "channel", locationName, camera.name, view.channel)
    const channel = camera.channels.find(({name}) => name === view.channel)
    if (!channel.per_day) {
      console.log(`${channel.name} is sequenced`)
      hasSequencedChannels = true
    }
  })
  if (hasSequencedChannels) {
    ws.subscribe("service", "camera", locationName, camera.name)
  }

  const mosaicRoot = createRoot(_getById("mosaic-view"))
  mosaicRoot.render(
    <React.StrictMode>
      <MosaicView
        locationName={locationName}
        camera={camera}
      />
    </React.StrictMode>
  )
})()
