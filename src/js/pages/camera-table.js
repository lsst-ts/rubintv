import React from "react"
import { createRoot } from "react-dom/client"
import TableApp from "../components/TableApp"
import PerDay from "../components/PerDay"
import Banner from "../components/Banner"
import { _getById } from "../modules/utils"
import { WebsocketClient } from "../modules/ws-service-client"
;(function () {
  if (window.APP_DATA.historicalBusy) {
    return
  }

  const {
    siteLocation,
    locationName,
    camera = {},
    tableChannels = {},
    tableMetadata = {},
    perDay = {},
    nightReportLink = "",
    date = "",
    isHistorical,
  } = window.APP_DATA

  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "camera", locationName, camera.name)
  }

  const bannerRoot = createRoot(_getById("header-banner"))
  bannerRoot.render(
    <Banner
      siteLocation={siteLocation}
      locationName={locationName}
      camera={camera}
    />
  )

  const tableRoot = createRoot(_getById("table"))
  tableRoot.render(
    <TableApp
      camera={camera}
      initialDate={date}
      initialChannelData={tableChannels}
      initialMetadata={tableMetadata}
    />
  )

  const perDayRoot = createRoot(_getById("per-day"))
  perDayRoot.render(
    <PerDay
      camera={camera}
      initialDate={date}
      initialPerDay={perDay}
      initialNRLink={nightReportLink}
    />
  )
})()
