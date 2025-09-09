import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
import MediaDisplay from "../components/MediaDisplay"
import { Camera, ExposureEvent } from "../components/componentTypes"
;(function () {
  const {
    locationName,
    camera = {} as Camera,
    channel,
    event = {} as ExposureEvent,
    isCurrent = false,
    prevNext,
    allChannelNames,
  } = window.APP_DATA

  if (isCurrent) {
    const ws = new WebsocketClient()
    ws.subscribe("channel", locationName, camera.name, channel.name)
  }

  // Render the MediaDisplay component instead of manually handling DOM updates
  const mediaDisplayElement = _getById("event-display")
  if (!mediaDisplayElement) {
    console.error("Event display element not found")
    return
  }
  const mediaDisplayRoot = createRoot(mediaDisplayElement)
  mediaDisplayRoot.render(
    <MediaDisplay
      locationName={locationName}
      camera={camera}
      initEvent={event}
      prevNext={prevNext}
      allChannelNames={allChannelNames}
      isCurrent={isCurrent}
    />
  )
})()
