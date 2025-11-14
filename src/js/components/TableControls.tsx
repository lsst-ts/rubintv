import React, {
  useEffect,
  useState,
  useContext,
  KeyboardEvent,
  useMemo,
} from "react"
import Clock, { TimeSinceLastImageClock } from "./Clock"
import {
  _getById,
  findPrevNextDate,
  getCameraPageForDateUrl,
  getImageAssetUrl,
  unpackCalendarAsDateList,
} from "../modules/utils"
import { saveColumnSelection } from "../modules/columnStorage"
import {
  Metadata,
  RubinTVContextType,
  AboveTableRowProps,
  TableControlProps,
  DownloadMetadataButtonProps,
  CalendarData,
} from "./componentTypes"
import { RubinTVTableContext } from "./contexts/contexts"

export default function AboveTableRow({
  locationName,
  camera,
  availableColumns,
  selected,
  setSelected,
  date,
  metadata,
  isHistorical,
  calendar,
  toggleCalendar,
}: AboveTableRowProps) {
  const [calendarData, setCalendarData] = useState<CalendarData | null>(
    calendar || null
  )

  useEffect(() => {
    function handleCalendarEvent(event: CustomEvent) {
      const { dataType, data: calendarData } = event.detail
      if (dataType !== "calendarUpdate") {
        return
      }
      setCalendarData(calendarData)
    }
    window.addEventListener("calendar", handleCalendarEvent as EventListener)
    return () => {
      window.removeEventListener(
        "calendar",
        handleCalendarEvent as EventListener
      )
    }
  }, [calendar])

  const dateList = useMemo(
    () => unpackCalendarAsDateList(calendarData || {}),
    [calendarData]
  )
  const { prevDate, nextDate } = findPrevNextDate(dateList, date)

  function handleJumpToDate(targetDate: string) {
    window.location.href = getCameraPageForDateUrl(
      locationName,
      camera.name,
      targetDate
    )
  }

  function handleKeyToggleCalendar(e: KeyboardEvent<HTMLSpanElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      if (typeof toggleCalendar === "function") {
        toggleCalendar()
      }
    }
  }

  return (
    <div className="row">
      <h3 id="the-date">
        {prevDate && (
          <button
            className="button jump-to-date prev-date"
            onClick={() => {
              handleJumpToDate(prevDate)
            }}
            aria-label="Jump to previous date"
          ></button>
        )}
        <span
          role="button"
          className="date"
          aria-label="Toggle calendar view"
          onClick={toggleCalendar}
          onKeyDown={handleKeyToggleCalendar}
          tabIndex={0}
        >
          {date}
        </span>
        {nextDate && (
          <button
            className="button jump-to-date next-date"
            onClick={() => {
              handleJumpToDate(nextDate)
            }}
            aria-label="Jump to next date"
          ></button>
        )}
      </h3>
      <TableControls
        cameraName={camera.name}
        availableColumns={availableColumns}
        selected={selected}
        setSelected={setSelected}
      />
      <DownloadMetadataButton
        date={date}
        cameraName={camera.name}
        metadata={metadata}
      />
      <Clock />
      {camera.time_since_clock && !isHistorical && (
        <TimeSinceLastImageClock
          metadata={metadata}
          camera={{
            ...camera,
            time_since_clock: camera.time_since_clock ?? { label: "" },
          }}
        />
      )}
    </div>
  )
}

function TableControls({
  cameraName,
  availableColumns: originalAvailableColumns,
  selected: originalSelected,
  setSelected,
}: TableControlProps) {
  const [controlsOpen, setControlsOpen] = useState(false)
  const { locationName } = useContext(RubinTVTableContext) as RubinTVContextType

  const selected = Array.isArray(originalSelected) ? originalSelected : []
  const availableColumns = Array.isArray(originalAvailableColumns)
    ? originalAvailableColumns
    : []

  // Handle clicks outside to close the panel
  useEffect(() => {
    function handleOutsideClick(e: MouseEvent) {
      if (
        controlsOpen &&
        (!(e.target instanceof HTMLElement) ||
          !e.target.closest(".table-panel"))
      ) {
        setControlsOpen(false)
      }
    }

    document.addEventListener("click", handleOutsideClick)
    return () => {
      document.removeEventListener("click", handleOutsideClick)
    }
  }, [controlsOpen])

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      setControlsOpen(false)
    }
  }

  function toggleControls(e: React.MouseEvent<HTMLButtonElement>) {
    e.stopPropagation()
    setControlsOpen((controlsOpen) => !controlsOpen)
  }

  const handleCheckboxChange = (name: string) => {
    const currentSelected = Array.isArray(selected) ? [...selected] : []

    let newSelected
    if (currentSelected.includes(name)) {
      newSelected = currentSelected.filter((attr) => attr !== name)
      if (newSelected.length === 0) {
        return
      }
    } else {
      newSelected = [...currentSelected, name]
    }

    saveColumnSelection(newSelected, locationName, cameraName)
    setSelected(newSelected)
  }

  let numControlColumns = 2
  if (availableColumns.length > 45) {
    numControlColumns = 3
  }
  const gridStyle = {
    columnCount: numControlColumns,
  }

  const panelContainerClass = !controlsOpen
    ? "table-controls-container"
    : "table-controls-container open"

  const renderCheckbox = (title: string) => {
    const isAvailable = availableColumns.includes(title)
    const isSelected = selected.includes(title)

    return (
      <div
        className={`table-option${!isAvailable ? " unavailable" : ""}`}
        key={title}
      >
        <label htmlFor={title}>
          <input
            type="checkbox"
            id={title}
            name={title}
            value={1}
            checked={isSelected}
            onChange={() => handleCheckboxChange(title)}
            onKeyDown={handleKeyDown}
            disabled={!isAvailable}
          />
          {title}
        </label>
      </div>
    )
  }

  return (
    <div className={panelContainerClass} id="table-controls">
      <button
        className="table-control-button"
        onClick={toggleControls}
        onKeyDown={handleKeyDown}
        title="Add/Remove Columns"
        aria-label="Add/Remove Columns"
        aria-expanded={controlsOpen}
        aria-controls="table-controls"
        aria-haspopup="true"
      >
        Add/Remove Columns
      </button>
      <div className="table-panel">
        {controlsOpen && (
          <div className="table-options" style={gridStyle}>
            {/* Show both available and unavailable selected columns */}
            {Array.from(new Set([...selected, ...availableColumns]))
              .sort((a, b) => a.localeCompare(b))
              .map(renderCheckbox)}
          </div>
        )}
      </div>
    </div>
  )
}

export function JumpButtons() {
  const jumpArrowImage = getImageAssetUrl("jump-arrow.svg")
  const handleTableJump = (toTop: boolean) => {
    const table = _getById("table-section") as HTMLTableElement
    table.scrollIntoView(toTop)
  }
  return (
    <div className="jump-buttons">
      <button
        onClick={() => handleTableJump(true)}
        className="jump-button to-top"
        title="to top"
      >
        <img src={jumpArrowImage} />
      </button>
      <button
        onClick={() => handleTableJump(false)}
        className="jump-button to-bottom"
        title="to bottom"
      >
        <img src={jumpArrowImage} />
      </button>
    </div>
  )
}

function DownloadMetadataButton({
  date,
  cameraName,
  metadata,
}: DownloadMetadataButtonProps) {
  return (
    <button
      className="button button-small download-metadata"
      onClick={() => downloadMetadata(date, cameraName, metadata)}
    >
      Download Metadata
    </button>
  )
}

function downloadMetadata(
  date: string,
  cameraName: string,
  metadata: Metadata | null
) {
  const a = document.createElement("a")
  const blob = new Blob([JSON.stringify(metadata)])
  const url = URL.createObjectURL(blob)
  a.href = url
  a.download = `${cameraName}_${date}.json`
  a.click()
  URL.revokeObjectURL(url)
}
