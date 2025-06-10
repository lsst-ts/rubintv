import React, { useState, useEffect, useCallback } from "react"
import PropTypes from "prop-types"
import TableView, { TableHeader } from "./TableView"
import AboveTableRow, { JumpButtons } from "./TableControls"
import { _getById, union, getHistoricalData } from "../modules/utils"
import {
  loadColumnSelection,
  saveColumnSelection,
} from "../modules/columnStorage"
import { cameraType } from "./componentPropTypes"
import { ModalProvider } from "./Modal"

export default function TableApp({
  camera,
  initialDate,
  isHistorical,
  initialChannelData = {},
  initialMetadata = {},
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

  // Column configuration derived from camera metadata
  const defaultColumns = camera.metadata_cols
    ? Object.entries(camera.metadata_cols).map(([name, desc]) => ({
        name,
        desc,
      }))
    : []
  const defaultColNames = defaultColumns.map((col) => col.name)
  const availableColumns = getAllColumnNames(metadata, defaultColNames)

  // Load selected columns from storage
  const [selected, setSelected] = useState(() => {
    return loadColumnSelection(locationName, camera.name, defaultColNames)
  })

  // Save selection changes
  const handleSetSelected = useCallback(
    (newSelected) => {
      setSelected(newSelected)
      saveColumnSelection(newSelected, locationName, camera.name)
    },
    [locationName, camera.name]
  )

  const selectedObjs = selected.map((c) => ({ name: c }))
  const selectedMetaCols = defaultColumns
    .filter((col) => selected.includes(col.name))
    .concat(selectedObjs.filter((o) => !defaultColNames.includes(o.name)))

  // Fetch historical data if required.
  // This effect runs only once when the component mounts.
  useEffect(() => {
    if (!isHistorical) {
      return
    }
    getHistoricalData(locationName, camera.name, date)
      .then((json) => {
        const data = JSON.parse(json)
        for (const key in data) {
          const notifier = new CustomEvent("camera", {
            detail: {
              datestamp: date,
              data: data[key],
              dataType: key,
            },
          })
          window.dispatchEvent(notifier)
        }
      })
      .catch((error) => {
        console.error("Error fetching historical data:", error)
      })
  }, [])

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

  const handleCameraEvent = useCallback(
    (event) => {
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
    },
    [date]
  )

  useEffect(() => {
    window.addEventListener("camera", handleCameraEvent)
    return () => {
      window.removeEventListener("camera", handleCameraEvent)
    }
  }, [handleCameraEvent])

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
            availableColumns={availableColumns}
            selected={selected}
            setSelected={handleSetSelected}
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
          sortOn={sortOn}
        />
      </ModalProvider>
    </div>
  )
}
TableApp.propTypes = {
  camera: cameraType.isRequired,
  /** Date given when first landing on the page. */
  initialDate: PropTypes.string.isRequired,
  /** true if this is a historical page */
  isHistorical: PropTypes.bool,
  /** Initial channel data */
  initialChannelData: PropTypes.object,
  /** Initial metadata */
  initialMetadata: PropTypes.object,
}

function getAllColumnNames(metadata, defaultColNames) {
  // get the set of all data for list of all available attrs
  const availableColumns = Object.values(metadata)
    .map((obj) => Object.keys(obj))
    .flat()
    .sort()
  // get the set of all data for list of all available attrs
  const uniqueColNames = Array.from(
    new Set(defaultColNames.concat(availableColumns))
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
