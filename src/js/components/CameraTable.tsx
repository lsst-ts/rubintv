import React, { StrictMode, useRef } from "react"
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
  noDataForDay,
}: CameraTableProps) {
  const calendarRef = React.useRef<HTMLElement>(null)
  const isClosed = useRef(true)

  function toggleCalendar() {
    isClosed.current = !isClosed.current
    if (calendarRef.current) {
      calendarRef.current.classList.toggle("closed")
      if (!isClosed.current && !isElementInViewport(calendarRef.current)) {
        calendarRef.current.scrollIntoView()
      }
    }
  }
  React.useEffect(() => {
    if (noDataForDay) {
      toggleCalendar()
    }
  }, [noDataForDay])
  return (
    <StrictMode>
      <section ref={calendarRef} id="calendar" className="calendar closed">
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
          noDataForDay={noDataForDay}
        />
      </section>
    </StrictMode>
  )
}
