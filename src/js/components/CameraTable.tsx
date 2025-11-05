import React, { StrictMode } from "react"
import RubinCalendar from "./RubinCalendar"
import CurrentChannels from "./CurrentChannels"
import PerDay from "./PerDay"
import TableApp from "./TableApp"
import { CameraTableProps } from "./componentTypes"
import { isElementInViewport } from "../modules/utils"

export default function CameraTable({
  siteLocation,
  locationName,
  camera,
  nightReportLink,
  date,
  isHistorical,
  calendar,
  isStale,
  seqNums,
}: CameraTableProps) {
  const [isClosed, setIsClosed] = React.useState(true)

  function toggleCalendar() {
    setIsClosed(!isClosed)
    if (isClosed) {
      const calendarElement = document.getElementById("calendar")
      if (calendarElement && !isElementInViewport(calendarElement)) {
        calendarElement.scrollIntoView()
      }
    }
  }
  return (
    <StrictMode>
      <section
        id="calendar"
        className={`calendar ${isClosed ? "closed" : "open"}`}
      >
        <RubinCalendar
          selectedDate={date}
          initialCalendarData={calendar}
          camera={camera}
          locationName={locationName}
        />
      </section>
      {!isHistorical && (
        <CurrentChannels locationName={locationName} camera={camera} />
      )}
      <section className="per-day-section">
        <PerDay
          camera={camera}
          initialDate={date}
          initialNRLink={nightReportLink}
          locationName={locationName}
          isHistorical={isHistorical}
        />
      </section>
      <section className="table-section" id="table-section">
        <TableApp
          siteLocation={siteLocation}
          locationName={locationName}
          camera={camera}
          initialDate={date}
          isStale={isStale}
          isHistorical={isHistorical}
          seqNums={seqNums}
          calendar={calendar}
          toggleCalendar={toggleCalendar}
        />
      </section>
    </StrictMode>
  )
}
