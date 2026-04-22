import React, { useState, useEffect, useCallback } from "react"
import TableView, { TableHeader } from "./TableView"
import AboveTableRow, { JumpButtons } from "./TableControls"
import { union } from "../modules/utils"
import {
  loadColumnSelection,
  saveColumnSelection,
} from "../modules/columnStorage"
import { ModalProvider } from "./Modal"
import {
  TableAppProps,
  Metadata,
  MetadataColumn,
  FilterOptions,
  SortingOptions,
} from "./componentTypes"
import { RubinTVTableContext } from "./contexts/contexts"
import useTableData from "../hooks/useTableData"

export default function TableApp({
  camera,
  locationName,
  initialDate,
  isHistorical,
  siteLocation,
  isStale,
  seqNums,
  calendar,
  toggleCalendar,
}: TableAppProps) {
  const {
    date,
    channelData,
    metadata,
    hasReceivedData,
    isLoadingMetadata,
    metadataBytesReceived,
    metadataTotalSize,
    lastKnownMetadataRow,
    error,
  } = useTableData({
    camera,
    locationName,
    initialDate,
    isHistorical,
    isStale,
  })

  const [filterOn, setFilterOn] = useState({
    column: "",
    value: "",
  } as FilterOptions)
  const [sortOn, setSortOn] = useState({
    column: "seq",
    order: "desc",
  } as SortingOptions)

  // Column configuration derived from camera metadata
  const defaultColumns = camera.metadata_columns
    ? Object.entries(camera.metadata_columns).map(
        ([name, desc]) =>
          ({
            name,
            desc,
          }) as MetadataColumn
      )
    : []
  const defaultColNames = defaultColumns.map((col) => col.name)
  const availableColumns = getAllColumnNames(metadata, defaultColNames)

  // Load selected columns from storage
  const [selected, setSelected] = useState(() => {
    return loadColumnSelection(locationName, camera.name, defaultColNames)
  })

  // Save selection changes
  const handleSetSelected = useCallback(
    (newSelected: string[]) => {
      setSelected(newSelected)
      saveColumnSelection(newSelected, locationName, camera.name)
    },
    [locationName, camera.name]
  )

  const selectedObjs = selected.map((columnName) => ({ name: columnName }))
  const metaColumnsToDisplay = defaultColumns
    .filter((col) => selected.includes(col.name))
    .concat(
      selectedObjs.filter(
        (o: MetadataColumn) =>
          !defaultColNames.includes(o.name) && availableColumns.includes(o.name)
      )
    )

  // convenience var for showing filterColumn has been set
  const filterColumnSet = filterOn.column !== "" && filterOn.value !== ""

  // filter from metadata the rows that have the filterRowsOn value
  // in the filterRowsOn column.
  let filteredMetadata = metadata
  let filteredChannelData = channelData
  if (filterColumnSet) {
    filteredMetadata = Object.entries(metadata).reduce((acc, [key, val]) => {
      if (String(val[filterOn.column] as string) === filterOn.value) {
        acc[key] = val
      }
      return acc
    }, {} as Metadata)
    // reduce the channelData to only the rows that are in the filteredMetadata
    filteredChannelData = Object.entries(channelData).reduce(
      (acc, [key, val]) => {
        if (filteredMetadata[key]) {
          acc[key] = val
        }
        return acc
      },
      {} as typeof channelData
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
  }, [filteredMetadata, filteredChannelData, selected])

  if (unfilteredRowsCount == 0 && hasReceivedData) {
    return <h3>There is no data for this day</h3>
  } else if (!hasReceivedData) {
    const colours = camera.channels.map((c) => c.colour)
    return (
      <div className="loading-container">
        {isLoadingMetadata ? (
          <MetadataProgressBar
            bytesReceived={metadataBytesReceived}
            totalSize={metadataTotalSize}
            colours={colours}
          />
        ) : (
          <>
            <LoadingBar colours={colours} />
            <h3>Loading data for {date}...</h3>
          </>
        )}
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h3>Error: {error}</h3>
      </div>
    )
  }

  return (
    <RubinTVTableContext.Provider
      value={{ siteLocation, locationName, camera, dayObs: date }}
    >
      <div className="table-container">
        {isLoadingMetadata && (
          <MetadataProgressBar
            bytesReceived={metadataBytesReceived}
            totalSize={metadataTotalSize}
            colours={camera.channels.map((c) => c.colour)}
          />
        )}
        <ModalProvider>
          <div className="above-table-sticky">
            <AboveTableRow
              locationName={locationName}
              camera={camera}
              availableColumns={availableColumns}
              selected={selected}
              setSelected={handleSetSelected}
              date={date}
              calendar={calendar}
              toggleCalendar={toggleCalendar}
              metadata={metadata}
              lastKnownMetadataRow={lastKnownMetadataRow}
              isHistorical={isHistorical}
            />
            <div className="table-header row">
              <TableHeader
                camera={camera}
                metadataColumns={metaColumnsToDisplay}
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
            metadataColumns={metaColumnsToDisplay}
            filterOn={filterOn}
            filteredRowsCount={filteredRowsCount}
            sortOn={sortOn}
            siteLocation={siteLocation}
            seqNumsToShow={seqNums}
          />
        </ModalProvider>
      </div>
    </RubinTVTableContext.Provider>
  )
}

function LoadingBar({
  colours = ["#b0e0e6", "#87ceeb", "#4682b4", "#87ceeb"],
}: {
  colours: string[]
}) {
  // Create a gradient for the loading bar based on the channel colours
  const gradientStops: string[] = []
  colours.forEach((colour, index) => {
    gradientStops.push(
      `${colour} ${Math.round(index * (100 / colours.length))}%`
    )
  })
  gradientStops.push(`${colours[0]} 100%`)
  const gradient = `linear-gradient(90deg, ${gradientStops.join(", ")})`
  return (
    <div className="loading-bar-container">
      <div
        style={{ background: gradient, backgroundSize: "25% 100%" }}
        className="loading-bar-animated"
      ></div>
    </div>
  )
}

function MetadataProgressBar({
  bytesReceived,
  totalSize,
  colours,
}: {
  bytesReceived: number
  totalSize: number
  colours: string[]
}) {
  const progress =
    totalSize > 0
      ? Math.min(99, Math.round((bytesReceived / totalSize) * 100))
      : 0

  const gradientStops: string[] = []
  colours.forEach((colour, index) => {
    gradientStops.push(
      `${colour} ${Math.round(index * (100 / colours.length))}%`
    )
  })
  gradientStops.push(`${colours[0]} 100%`)
  const gradient = `linear-gradient(90deg, ${gradientStops.join(", ")})`

  return (
    <>
      <div className="loading-bar-container">
        <div
          className="metadata-progress-bar"
          style={{
            background: gradient,
            backgroundSize: "25% 100%",
            clipPath: `inset(0 ${100 - progress}% 0 0)`,
          }}
        ></div>
      </div>
      <h3>Retrieving metadata...</h3>
    </>
  )
}

function getAllColumnNames(metadata: Metadata, defaultColNames: string[]) {
  // get the set of all data for list of all available attrs
  const availableColumns = Object.values(metadata)
    .map((obj) => Object.keys(obj))
    .flat()
    .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
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
  for (let ix = 0; ix < headers.length; ix++) {
    const title = headers[ix] as HTMLElement
    const width = columns[ix] + 2
    title.style.left = `${sum}px`
    sum += width
  }
  if (sum > 0) {
    const sumWidth = `${Math.ceil(sum) + 2}px`
    const aboveTable = document.querySelector(
      ".above-table-sticky"
    ) as HTMLElement
    const tableHeader = document.querySelector(".table-header") as HTMLElement
    if (aboveTable) {
      aboveTable.style.width = sumWidth
    }
    if (tableHeader) {
      tableHeader.style.width = sumWidth
    }
  }
}
