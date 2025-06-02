import React, { useEffect, useState } from "react"
import PropTypes from "prop-types"
import Clock, { TimeSinceLastImageClock } from "./Clock"
import { _getById } from "../modules/utils"
import { cameraType, metadataType } from "./componentPropTypes"
import { saveColumnSelection } from "../modules/columnStorage"

export default function AboveTableRow({
  camera,
  allColNames,
  selected,
  setSelected,
  date,
  metadata,
  isHistorical,
}) {
  return (
    <div className="row">
      <h3 id="the-date">
        Data for day: <span className="date">{date}</span>
      </h3>
      <TableControls
        cameraName={camera.name}
        allColNames={allColNames}
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
        <TimeSinceLastImageClock camera={camera} metadata={metadata} />
      )}
    </div>
  )
}
AboveTableRow.propTypes = {
  /** the camera object */
  camera: cameraType,
  /** the names of all metadata columns */
  allColNames: PropTypes.arrayOf(PropTypes.string),
  /** the names of the currently selected columns to display */
  selected: PropTypes.arrayOf(PropTypes.string),
  /** callback function from the parent component TableApp */
  setSelected: PropTypes.func,
  /** the given date */
  date: PropTypes.string,
  /** the current metadata for this camera/date */
  metadata: metadataType,
  /** true if this is a historical page */
  isHistorical: PropTypes.bool,
}

function TableControls({ cameraName, allColNames, selected, setSelected }) {
  const [controlsOpen, setControlsOpen] = useState(false)

  const locationName = window.APP_DATA.locationName

  // Handle clicks outside to close the panel
  useEffect(() => {
    function handleOutsideClick(e) {
      if (controlsOpen && !e.target.closest(".table-panel")) {
        setControlsOpen(false)
      }
    }

    window.addEventListener("click", handleOutsideClick)
    return () => {
      window.removeEventListener("click", handleOutsideClick)
    }
  }, [controlsOpen])

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      setControlsOpen(false)
    }
  }

  function toggleControls(e) {
    e.stopPropagation()
    setControlsOpen((controlsOpen) => !controlsOpen)
  }

    const handleCheckboxChange = (name) => {
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
  if (allColNames.length > 45) {
    numControlColumns = 3
  }
  const gridStyle = {
    columnCount: numControlColumns,
  }

  const panelContainerClass = !controlsOpen
    ? "table-controls-container"
    : "table-controls-container open"

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
            {allColNames.map((title) => (
              <div className="table-option" key={title}>
                <label htmlFor={title}>
                  <input
                    type="checkbox"
                    id={title}
                    name={title}
                    value={1}
                    checked={selected.includes(title)}
                    onChange={() => handleCheckboxChange(title)}
                    onKeyDown={handleKeyDown}
                  />
                  {title}
                </label>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
TableControls.propTypes = {
  /** the names of all metadata columns */
  allColNames: PropTypes.arrayOf(PropTypes.string),
  /** the name of the current camera */
  cameraName: PropTypes.string,
  /** the names of the currently selected columns to display */
  selected: PropTypes.arrayOf(PropTypes.string),
  /** callback function from the parent component TableApp */
  setSelected: PropTypes.func,
  /** the given date */
  date: PropTypes.string,
  /** the current metadata for this camera/date */
  metadata: metadataType,
  /** true if this is a historical page */
  isHistorical: PropTypes.bool,
}

export function JumpButtons() {
  const { pathPrefix } = window.APP_DATA
  return (
    <div className="jump-buttons">
      <button
        onClick={() => _getById("table").scrollIntoView()}
        className="jump-button to-top"
        title="to top"
      >
        <img src={pathPrefix + "/static/images/jump-arrow.svg"} />
      </button>
      <button
        onClick={() => _getById("table").scrollIntoView(false)}
        className="jump-button to-bottom"
        title="to bottom"
      >
        <img src={pathPrefix + "/static/images/jump-arrow.svg"} />
      </button>
    </div>
  )
}

function DownloadMetadataButton({ date, cameraName, metadata }) {
  return (
    <button
      className="button button-small download-metadata"
      onClick={() => downloadMetadata(date, cameraName, metadata)}
    >
      Download Metadata
    </button>
  )
}
DownloadMetadataButton.propTypes = {
  cameraName: PropTypes.string,
  date: PropTypes.string,
  metadata: PropTypes.object,
}

function downloadMetadata(date, cameraName, metadata) {
  const a = document.createElement("a")
  const blob = new Blob([JSON.stringify(metadata)])
  const url = window.URL.createObjectURL(blob)
  a.href = url
  a.download = `${cameraName}_${date}.json`
  a.click()
  URL.revokeObjectURL(blob.name)
}
