import React from "react"
import { createRoot } from "react-dom/client"
import TableApp from "../components/TableApp"
import PerDay from "../components/PerDay"
import Banner from "../components/Banner"
import RubinCalendar from "../components/RubinCalendar"
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
    channelData = {},
    metadata = {},
    perDay = {},
    nightReportLink = "",
    date = "",
    isHistorical,
    calendar,
  } = window.APP_DATA

  const bannerRoot = createRoot(_getById("header-banner"))
  bannerRoot.render(
    <Banner
      siteLocation={siteLocation}
      locationName={locationName}
      camera={camera}
    />
  )

  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("service", "camera", locationName, camera.name)
  } else {
    const ws = new WebsocketClient()
    ws.subscribe("service", "calendar", locationName, camera.name)

    const calendarRoot = createRoot(_getById("calendar"))
    calendarRoot.render(
      <RubinCalendar
        selectedDate={date}
        initialCalendarData={calendar}
        camera={camera}
        locationName={locationName}
      />
    )
  }

  const tableRoot = createRoot(_getById("table"))
  tableRoot.render(
    <TableApp
      camera={camera}
      initialDate={date}
      initialChannelData={channelData}
      initialMetadata={metadata}
      isHistorical={isHistorical}
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
