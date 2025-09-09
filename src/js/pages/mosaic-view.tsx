import React from "react"
import { createRoot } from "react-dom/client"
import { WebsocketClient } from "../modules/ws-service-client"
import MosaicView, { CameraWithMosaicViewMeta } from "../components/MosaicView"
import { _getById } from "../modules/utils"
;(function () {
  const locationName = window.APP_DATA.locationName || ""
  const camera = window.APP_DATA.camera || {}
  const ws = new WebsocketClient()
  ws.subscribe("historicalStatus")

  let hasSequencedChannels = null
  if (!camera.mosaic_view_meta || !Array.isArray(camera.mosaic_view_meta)) {
    console.error("Invalid mosaic view meta data for camera:", camera.name)
    return
  }
  camera.mosaic_view_meta.forEach((view) => {
    ws.subscribe("channel", locationName, camera.name, view.channel)
    const channel = camera.channels.find(({ name }) => name === view.channel)
    if (channel && !channel.per_day) {
      hasSequencedChannels = true
    }
  })
  if (hasSequencedChannels) {
    ws.subscribe("camera", locationName, camera.name)
  }

  const mosaicElement = _getById("mosaic-view")
  if (!mosaicElement) {
    console.error("Mosaic view element not found")
    return
  }
  const mosaicRoot = createRoot(mosaicElement)
  mosaicRoot.render(
    <React.StrictMode>
      <MosaicView
        locationName={locationName}
        camera={camera as CameraWithMosaicViewMeta}
      />
    </React.StrictMode>
  )
})()
