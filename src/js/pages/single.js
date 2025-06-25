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
    homeUrl,
    imgUrl,
    videoUrl,
    isCurrent,
    eventUrl,
    prevNext,
    allChannelNames,
  } = window.APP_DATA
  const channel = initEvent.channel_name

  if (isCurrent) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "channel", locationName, camera.name, channel)
  }

  // Set dateUrl to the address of the day's page
  const suffix = isCurrent ? "" : `date/${initEvent.day_obs}`
  const dateUrl = new URL(
    `${locationName}/${camera.name}/${suffix}`,
    homeUrl
  ).toString()

  // Render the MediaDisplay component instead of manually handling DOM updates
  const mediaDisplayRoot = createRoot(_getById("event-display"))
  mediaDisplayRoot.render(
    <MediaDisplay
      initialEvent={initEvent}
      imgUrl={imgUrl}
      videoUrl={videoUrl}
      dateUrl={dateUrl}
      camera={camera}
      metadata={metadata}
      eventUrl={eventUrl}
      prevNext={prevNext}
      allChannelNames={allChannelNames}
      isCurrent={isCurrent}
    />
  )
})()
