import { _getById, _elWithAttrs } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  const initEvent = window.APP_DATA.initEvent || null
  if (!initEvent) {
    return
  }
  const location = window.APP_DATA.locationName
  const camera = initEvent.camera_name
  const channel = initEvent.channel_name
  let baseImgURL = window.APP_DATA.imgURL.split("/").slice(0, -1).join("/")
  if (!baseImgURL.endsWith("/")) {
    baseImgURL += "/"
  }
  // eslint-disable-next-line no-unused-vars
  const ws = new WebsocketClient()
  ws.subscribe("service", "channel", location, camera, channel)

  window.addEventListener("channel", (message) => {
    const newEvent = message.detail.data
    if (!newEvent) {
      return
    }
    const { filename, day_obs: dayObs, seq_num: seqNum } = newEvent
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
