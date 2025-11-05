import React from "react"
import { createRoot } from "react-dom/client"
import Banner from "../components/Banner"
import CameraTable from "js/components/CameraTable"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
import { Camera } from "../components/componentTypes"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }
  const {
    siteLocation,
    locationName,
    camera = {} as Camera,
    nightReportLink = "",
    date = "",
    isHistorical,
    calendar,
    isStale = false,
    seqNums,
  } = window.APP_DATA

  const banner = _getById("header-banner")
  if (!banner) {
    console.error("Header banner element not found")
    return
  }
  const bannerRoot = createRoot(banner)
  bannerRoot.render(
    <Banner
      siteLocation={siteLocation}
      locationName={locationName}
      camera={camera}
    />
  )

  const ws = new WebsocketClient()
  ws.subscribe("calendar", locationName, camera.name)

  if (!isHistorical || isStale) {
    ws.subscribe("camera", locationName, camera.name)
  }

  const getCameraTableMain = _getById("camera-table-main")
  if (!getCameraTableMain) {
    console.error("Camera Table Main element not found")
    return
  }
  const cameraTableMainRoot = createRoot(getCameraTableMain)
  cameraTableMainRoot.render(
    <CameraTable
      siteLocation={siteLocation}
      locationName={locationName}
      camera={camera}
      nightReportLink={nightReportLink}
      date={date}
      isHistorical={isHistorical}
      calendar={calendar}
      isStale={isStale}
      seqNums={seqNums}
    />
  )
})()
