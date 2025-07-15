import React from "react"
import { createRoot } from "react-dom/client"
import TableApp from "../components/TableApp"
import PerDay from "../components/PerDay"
import Banner from "../components/Banner"
import RubinCalendar from "../components/RubinCalendar"
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

  if (!isHistorical) {
    const ws = new WebsocketClient()
    ws.subscribe("camera", locationName, camera.name)
  } else {
    const ws = new WebsocketClient()
    ws.subscribe("calendar", locationName, camera.name)

    const calendarElement = _getById("camera")
    if (!calendarElement) {
      console.error("Camera element not found")
      return
    }
    const calendarRoot = createRoot(calendarElement)
    calendarRoot.render(
      <RubinCalendar
        selectedDate={date}
        initialCalendarData={calendar}
        camera={camera}
        locationName={locationName}
      />
    )
  }

  const table = _getById("table")
  if (!table) {
    console.error("Table element not found")
    return
  }
  const tableRoot = createRoot(table)
  tableRoot.render(
    <TableApp
      camera={camera}
      initialDate={date}
      isHistorical={isHistorical}
      locationName={locationName}
      siteLocation={siteLocation}
    />
  )

  const perDayElement = _getById("per-day")
  if (!perDayElement) {
    console.error("Per Day element not found")
    return
  }
  const perDayRoot = createRoot(perDayElement)
  perDayRoot.render(
    <PerDay
      camera={camera}
      initialDate={date}
      initialNRLink={nightReportLink}
      locationName={locationName}
      isHistorical={isHistorical}
    />
  )
})()
