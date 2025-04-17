import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
import MediaDisplay from "../components/MediaDisplay"
;(function () {
  const initEvent = window.APP_DATA.initEvent || null
  if (!initEvent) {
    return
  }
  const {
    locationName,
    camera = {},
    metadata,
    imgUrl,
    videoUrl,
    isCurrent,
    eventUrl,
    prevNext,
  } = window.APP_DATA
  const channel = initEvent.channel_name

  // eslint-disable-next-line no-unused-vars
  if (isCurrent) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "channel", locationName, camera.name, channel)
    ws.subscribe("service", "camera", locationName, camera.name)
  }

  // Render the MediaDisplay component instead of manually handling DOM updates
  const mediaDisplayRoot = createRoot(_getById("event-display"))
  mediaDisplayRoot.render(
    <MediaDisplay
      initialEvent={initEvent}
      imgUrl={imgUrl}
      videoUrl={videoUrl}
      camera={camera}
      metadata={metadata}
      eventUrl={eventUrl}
      prevNext={prevNext}
      isCurrent={isCurrent}
    />
  )
})()
