import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import TableView, { TableHeader } from "./TableView"
import AboveTableRow, { JumpButtons } from "./TableControls"
import {
  _getById,
  intersect,
  union,
  retrieveSelected as retrieveStoredSelection,
} from "../modules/utils"
import { cameraType, channelDataType, metadataType } from "./componentPropTypes"
import { ModalProvider } from "./Modal"

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
  const [filterOn, setFilterOn] = useState({
    column: "",
    value: "",
  })
  const [sortOn, setSortOn] = useState({
    column: "seq",
    order: "desc",
  })

  const [error, setError] = useState(null)

  const locationName = window.APP_DATA.locationName

  // if they exist, convert metadata_cols into array of objects
  // from name: description to {name, desc}
  let defaultColumns
  if (camera.metadata_cols) {
    defaultColumns = Object.entries(camera.metadata_cols).map(
      ([name, desc]) => ({ name, desc })
    )
  } else {
    defaultColumns = []
  }
  const defaultColNames = defaultColumns.map((col) => col.name)
  const allColNames = getAllColumnNames(metadata, defaultColNames)

  const [selected, setSelected] = useState(() => {
    const storedColNames = retrieveStoredSelection(
      `${locationName}/${camera.name}`
    )
    if (storedColNames) {
      const intersectingColNames = intersect(storedColNames, allColNames)
      return intersectingColNames
    }
    return defaultColNames
  })

  const selectedObjs = selected.map((c) => ({ name: c }))
  const selectedMetaCols = defaultColumns
    .filter((col) => selected.includes(col.name))
    .concat(selectedObjs.filter((o) => !defaultColNames.includes(o.name)))

  // convenience var for showing filterColumn has been set
  const filterColumnSet = filterOn.column !== "" && filterOn.value !== ""

  // filter from metadata the rows that have the filterRowsOn value
  // in the filterRowsOn column.
  let filteredMetadata = metadata
  let filteredChannelData = channelData
  if (filterColumnSet) {
    filteredMetadata = Object.entries(metadata).reduce((acc, [key, val]) => {
      if (String(val[filterOn.column]) === filterOn.value) {
        acc[key] = val
      }
      return acc
    }, {})
    // reduce the channelData to only the rows that are in the filteredMetadata
    filteredChannelData = Object.entries(channelData).reduce(
      (acc, [key, val]) => {
        if (filteredMetadata[key]) {
          acc[key] = val
        }
        return acc
      },
      {}
    )
  }

  const unfilteredRowsCount = union(
    Object.keys(metadata),
    Object.keys(channelData)
  ).length
  const filteredRowsCount = union(
    Object.keys(filteredMetadata),
    Object.keys(filteredChannelData)
  ).length

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
      const headerDate = _getById("header-date")
      headerDate.textContent = datestamp
      headerDate.classList.remove("stale")
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

  if (unfilteredRowsCount == 0) {
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
      <ModalProvider>
        <div className="above-table-sticky">
          <AboveTableRow
            camera={camera}
            allColNames={allColNames}
            selected={selected}
            setSelected={setSelected}
            date={date}
            metadata={metadata}
            isHistorical={isHistorical}
            filterOn={filterOn}
          />
          <div className="table-header row">
            <TableHeader
              camera={camera}
              metadataColumns={selectedMetaCols}
              filterOn={filterOn}
              setFilterOn={setFilterOn}
              filteredRowsCount={filteredRowsCount}
              unfilteredRowsCount={unfilteredRowsCount}
              sortOn={sortOn}
              setSortOn={setSortOn}
            />
          </div>
          <JumpButtons></JumpButtons>
        </div>
        <TableView
          camera={camera}
          channelData={filteredChannelData}
          metadata={filteredMetadata}
          metadataColumns={selectedMetaCols}
          filterOn={filterOn}
          filteredRowsCount={filteredRowsCount}
        />
      </ModalProvider>
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

function getAllColumnNames(metadata, defaultColNames) {
  // get the set of all data for list of all available attrs
  const allColNames = Object.values(metadata)
    .map((obj) => Object.keys(obj))
    .flat()
    .sort()
  // get the set of all data for list of all available attrs
  const uniqueColNames = Array.from(
    new Set(defaultColNames.concat(allColNames))
  )
  // filter out the indicators (first char is '_')
  // and the replacement strings for empty channels
  // (first char is '@')
  const filtered = uniqueColNames.filter(
    (el) => !(el[0] === "_" || el[0] === "@")
  )
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

/**
 * Redraws the header widths based on the current table column widths.
 */
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
