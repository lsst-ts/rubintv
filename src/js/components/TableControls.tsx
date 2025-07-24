import React, { useEffect, useState, useContext, KeyboardEvent } from "react"
import Clock, { TimeSinceLastImageClock } from "./Clock"
import { _getById, getImageAssetUrl } from "../modules/utils"
import { saveColumnSelection } from "../modules/columnStorage"
import {
  Camera,
  Metadata,
  RubinTVTableContext,
  RubinTVContextType,
} from "./componentTypes"

export default function AboveTableRow({
  camera,
  availableColumns,
  selected,
  setSelected,
  date,
  metadata,
  isHistorical,
}: {
  camera: Camera
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
  date: string
  metadata: Metadata
  isHistorical: boolean
}) {
  return (
    <div className="row">
      <h3 id="the-date">
        Data for day: <span className="date">{date}</span>
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
  availableColumns,
  selected,
  setSelected,
}: {
  cameraName: string
  availableColumns: string[]
  selected: string[]
  setSelected: (selected: string[]) => void
}) {
  const [controlsOpen, setControlsOpen] = useState(false)
  const { locationName } = useContext(RubinTVTableContext) as RubinTVContextType

  selected = Array.isArray(selected) ? selected : []
  availableColumns = Array.isArray(availableColumns) ? availableColumns : []

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
              .slice()
              .sort((a, b) => a.localeCompare(b))
              .map(renderCheckbox)}
          </div>
        )}
      </div>
    </div>
  )
}

export function JumpButtons() {
  const table = _getById("table") as HTMLTableElement
  const jumpArrowImage = getImageAssetUrl("jump-arrow.svg")
  return (
    <div className="jump-buttons">
      <button
        onClick={() => table.scrollIntoView()}
        className="jump-button to-top"
        title="to top"
      >
        <img src={jumpArrowImage} />
      </button>
      <button
        onClick={() => table.scrollIntoView(false)}
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
}: {
  date: string
  cameraName: string
  metadata: Metadata
}) {
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
  metadata: Metadata
) {
  const a = document.createElement("a")
  const blob = new Blob([JSON.stringify(metadata)])
  const url = URL.createObjectURL(blob)
  a.href = url
  a.download = `${cameraName}_${date}.json`
  a.click()
  URL.revokeObjectURL(url)
}
