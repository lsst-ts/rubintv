import React from "react"
import { createRoot } from "react-dom/client"
import { TimeSinceLastImageClock } from "../components/Clock"
import { _getById, _elWithAttrs } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  const initEvent = window.APP_DATA.initEvent || null
  if (!initEvent) {
    return
  }
  const { locationName, camera = {}, imgURL, metadata } = window.APP_DATA
  const channel = initEvent.channel_name
  let baseImgURL = imgURL.split("/").slice(0, -1).join("/")
  if (!baseImgURL.endsWith("/")) {
    baseImgURL += "/"
  }
  // eslint-disable-next-line no-unused-vars
  const ws = new WebsocketClient()
  ws.subscribe("service", "channel", locationName, camera.name, channel)
  ws.subscribe("service", "camera", locationName, camera.name)

  const timeSinceRoot = createRoot(_getById("time-since-clock"))
  timeSinceRoot.render(
    <TimeSinceLastImageClock metadata={metadata} camera={camera} />
  )

  window.addEventListener("channel", (message) => {
    const { data, dataType } = message.detail
    if (dataType !== "event" || !data) {
      return
    }
    const { filename, day_obs: dayObs, seq_num: seqNum } = data
    _getById("date").textContent = dayObs
    _getById("seqNum").textContent = seqNum
    _getById("eventName").textContent = filename
    const oldImg = _getById("eventImage")
    // create new responsive <img> element
    const imgSrc = new URL(filename, baseImgURL)
    const newImg = _elWithAttrs("img", {
      class: "resp",
      id: oldImg.id,
      src: imgSrc,
    })
    newImg.addEventListener("load", () => {
      oldImg.replaceWith(newImg)
      _getById("eventLink").href = imgSrc
    })
  })
})()
