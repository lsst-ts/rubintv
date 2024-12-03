import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import TableView, { TableHeader } from "./TableView"
import AboveTableRow, { JumpButtons } from "./TableControls"
import { _getById, intersect, retrieveSelected } from "../modules/utils"
import { cameraType, channelDataType, metadataType } from "./componentPropTypes"

export default function TableApp({
  camera,
  initialDate,
  initialChannelData,
  initialMetadata,
  isHistorical,
}) {
  const [date, setDate] = useState(initialDate)
  const [channelData, setChannelData] = useState(initialChannelData)
  const [metadata, setMetadata] = useState(initialMetadata)
  const [error, setError] = useState(null)

  const locationName = window.APP_DATA.locationName

  // convert metadata_cols into array of objects if they exist
  let defaultCols
  if (camera.metadata_cols) {
    defaultCols = Object.entries(camera.metadata_cols).map(([name, desc]) => {
      return { name, desc }
    })
  } else {
    defaultCols = []
  }
  const defaultColNames = defaultCols.map((col) => col.name)
  const allColNames = getAllColumnNames(metadata, defaultColNames)

  const [selected, setSelected] = useState(() => {
    const savedColumns = retrieveSelected(`${locationName}/${camera.name}`)
    if (savedColumns) {
      const intersectedColumns = intersect(savedColumns, allColNames)
      return intersectedColumns
    }
    return defaultColNames
  })

  const selectedObjs = selected.map((c) => {
    return { name: c }
  })
  const selectedMetaCols = defaultCols
    .filter((c) => selected.includes(c.name))
    .concat(selectedObjs.filter((o) => !defaultColNames.includes(o.name)))

  useEffect(() => {
    redrawHeaderWidths()
  })

  function handleCameraEvent(event) {
    const { datestamp, data, dataType } = event.detail
    // if there's no data, don't update
    if (Object.entries(data).length === 0) {
      return
    }

    if (data.error) {
      setError(data.error)
    }

    if (datestamp && datestamp !== date) {
      window.APP_DATA.date = datestamp
      _getById("header-date").textContent = datestamp
      setDate(datestamp)
      setMetadata({})
      setChannelData({})
    }

    if (dataType === "metadata") {
      setMetadata(data)
    } else if (dataType === "channelData") {
      setChannelData(data)
    }
  }

  useEffect(() => {
    window.addEventListener("camera", handleCameraEvent)
    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("camera", handleCameraEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  if (
    Object.entries(metadata).length + Object.entries(channelData).length ==
    0
  ) {
    return <h3>There is no data for this day</h3>
  }

  if (error) {
    return (
      <div>
        <h3>Error: {error}</h3>
      </div>
    )
  }

  return (
    <div className="table-container">
      <div className="above-table-sticky">
        <AboveTableRow
          camera={camera}
          allColNames={allColNames}
          selected={selected}
          setSelected={setSelected}
          date={date}
          metadata={metadata}
          isHistorical={isHistorical}
        />
        <div className="table-header row">
          <TableHeader camera={camera} metadataColumns={selectedMetaCols} />
        </div>
        <JumpButtons></JumpButtons>
      </div>
      <TableView
        camera={camera}
        channelData={channelData}
        metadata={metadata}
        metadataColumns={selectedMetaCols}
      />
    </div>
  )
}
TableApp.propTypes = {
  camera: cameraType,
  /** Date given when first landing on the page. */
  initialDate: PropTypes.string,
  /**  */
  initialChannelData: channelDataType,
  initialMetadata: metadataType,
  /** true if this is a historical page */
  isHistorical: PropTypes.bool,
}

// function getAllColumnNames(colNames, defaultColNames) {
//   return Array.from(new Set(defaultColNames.concat(colNames)))
// }

function getAllColumnNames(metadata, defaultColNames) {
  // get the set of all data for list of all available attrs
  const allColNames = Object.values(metadata)
    .map((obj) => Object.keys(obj))
    .flat()
  const uniqueColNames = Array.from(
    new Set(defaultColNames.concat(allColNames))
  )
  // filter out the indicators (first char is '_')
  // and the replacement strings for empty channels
  // (first char is '@')
  const filtered = uniqueColNames.filter(
    (el) => !(el[0] === "_" || el[0] === "@")
  )
  console.log("Filtered:", filtered)
  return filtered
}

function getTableColumnWidths() {
  const tRow = document.querySelector("tr")
  if (!tRow) {
    return []
  }
  const cellsArr = Array.from(tRow.querySelectorAll("td"))
  const cellWidths = cellsArr.map((cell) => {
    return cell.offsetWidth
  })
  return cellWidths
}

function redrawHeaderWidths() {
  const columns = getTableColumnWidths()
  const headers = Array.from(document.querySelectorAll(".grid-title"))
  if (columns.length !== headers.length) {
    return
  }
  let sum = 0
  headers.forEach((title, ix) => {
    const width = columns[ix] + 2
    title.style.left = `${sum}px`
    sum += width
  })
  if (sum > 0) {
    const sumWidth = `${sum + 1}px`
    // add another 1px to the sticky elements to allow for any rounding down
    // of non-integer table widths
    document.querySelector(".above-table-sticky").style.width = sumWidth
    document.querySelector(".table-header").style.width = sumWidth
  }
}
