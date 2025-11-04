import React, { StrictMode } from "react"
import RubinCalendar from "./RubinCalendar"
import CurrentChannels from "./CurrentChannels"
import PerDay from "./PerDay"
import TableApp from "./TableApp"
import { CameraTableProps } from "./componentTypes"

export default function CameraTable({
  siteLocation,
  locationName,
  camera,
  nightReportLink,
  date,
  isHistorical,
  calendar,
  isStale,
  seqNum,
}: CameraTableProps) {
  const [isClosed, setIsClosed] = React.useState(true)
  function toggleCalendar() {
    setIsClosed(!isClosed)
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
      <PerDay
        camera={camera}
        initialDate={date}
        initialNRLink={nightReportLink}
        locationName={locationName}
        isHistorical={isHistorical}
      />
      <TableApp
        siteLocation={siteLocation}
        locationName={locationName}
        camera={camera}
        initialDate={date}
        isStale={isStale}
        isHistorical={isHistorical}
        seqNum={seqNum}
        calendar={calendar}
        toggleCalendar={toggleCalendar}
      />
    </StrictMode>
  )
}
