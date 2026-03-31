import React, { useState, useEffect, useCallback, useMemo } from "react"
import TableView, { TableHeader } from "./TableView"
import AboveTableRow, { JumpButtons } from "./TableControls"
import { _getById, union, getHistoricalData } from "../modules/utils"
import { createTableFromStructuredData } from "../modules/convertTableData"
import {
  loadColumnSelection,
  saveColumnSelection,
} from "../modules/columnStorage"
import { ModalProvider } from "./Modal"
import {
  TableAppProps,
  ChannelData,
  Metadata,
  MetadataRow,
  MetadataColumn,
  FilterOptions,
  SortingOptions,
} from "./componentTypes"
import { RubinTVTableContext } from "./contexts/contexts"
import {
  getAllColumnNames,
  redrawHeaderWidths,
  getDefaultColumns,
} from "../modules/tableUtils"

type EL = EventListener

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
  const [isReadyToDisplay, setIsReadyToDisplay] = useState(false)
  const [hasReceivedData, setHasReceivedData] = useState(false)
  const [date, setDate] = useState(initialDate)
  const [channelData, setChannelData] = useState({} as ChannelData)
  const [metadata, setMetadata] = useState({} as Metadata)
  const [filterOn, setFilterOn] = useState({
    column: "",
    value: "",
  } as FilterOptions)
  const [sortOn, setSortOn] = useState({
    column: "seq",
    order: "desc",
  } as SortingOptions)
  const [lastKnownMetadataRow, setLastKnownMetadataRow] = useState<
    MetadataRow | undefined
  >(undefined)

  const [error, setError] = useState(null)

  const defaultColumns = useMemo(() => getDefaultColumns(camera), [camera])
  const defaultColNames = useMemo(
    () => defaultColumns.map((col) => col.name),
    [defaultColumns]
  )
  const availableColumns = useMemo(
    () => getAllColumnNames(metadata, defaultColNames),
    [metadata, defaultColNames]
  )

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

  const metaColumnsToDisplay = useMemo(() => {
    const selectedObjs = selected.map((columnName) => ({ name: columnName }))
    return defaultColumns
      .filter((col) => selected.includes(col.name))
      .concat(
        selectedObjs.filter(
          (o: MetadataColumn) =>
            !defaultColNames.includes(o.name) &&
            availableColumns.includes(o.name)
        )
      )
  }, [defaultColumns, selected, defaultColNames, availableColumns])

  function setDateAndUpdateHeader(newDate: string, stale = false) {
    setDate(newDate)
    // Update header directly
    const headerDate = _getById("header-date") as HTMLSpanElement
    headerDate.textContent = newDate
    if (stale) {
      headerDate.classList.add("stale")
    } else {
      headerDate.classList.remove("stale")
    }
  }

  // Fetch historical data if required.
  // This effect runs only once when the component mounts.
  // It fetches data if the page is historical or stale.
  useEffect(() => {
    if (!isHistorical && !isStale) {
      return
    }
    getHistoricalData(locationName, camera.name, date)
      .then((json) => {
        const data = JSON.parse(json)
        if (data.metadata) setMetadata(data.metadata)
        if (data.structuredData && data.extensionInfo) {
          const channelData = createTableFromStructuredData(
            camera.name,
            date,
            data.structuredData,
            data.extensionInfo,
            camera.channels
          )
          setChannelData(channelData)
        }
        setDateAndUpdateHeader(data.date, isStale)
        setHasReceivedData(true)
      })
      .catch((error) => {
        console.error("Error fetching historical data:", error.message)
        setError(error.message || "Failed to fetch historical data")
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // convenience var for showing filterColumn has been set
  const filterColumnSet = filterOn.column !== "" && filterOn.value !== ""

  // filter from metadata the rows that have the filterRowsOn value
  // in the filterRowsOn column.
  const { filteredMetadata, filteredChannelData } = useMemo(() => {
    let filtered = metadata
    let filteredData = channelData
    if (filterColumnSet) {
      filtered = Object.entries(metadata).reduce((acc, [key, val]) => {
        if (String(val[filterOn.column] as string) === filterOn.value) {
          acc[key] = val
        }
        return acc
      }, {} as Metadata)
      // reduce the channelData to only the rows that are in the filteredMetadata
      filteredData = Object.entries(channelData).reduce((acc, [key, val]) => {
        if (filtered[key]) {
          acc[key] = val
        }
        return acc
      }, {} as ChannelData)
    }
    return { filteredMetadata: filtered, filteredChannelData: filteredData }
  }, [filterColumnSet, filterOn.column, filterOn.value, metadata, channelData])

  const { unfilteredRowsCount, filteredRowsCount } = useMemo(() => {
    const unfiltered = union(
      Object.keys(metadata),
      Object.keys(channelData)
    ).length
    const filtered = union(
      Object.keys(filteredMetadata),
      Object.keys(filteredChannelData)
    ).length
    return { unfilteredRowsCount: unfiltered, filteredRowsCount: filtered }
  }, [metadata, channelData, filteredMetadata, filteredChannelData])

  useEffect(() => {
    const redrawn = redrawHeaderWidths()
    if (redrawn) {
      setIsReadyToDisplay(true)
    }
  }, [filteredMetadata, filteredChannelData, selected])

  const handleCameraEvent = useCallback(
    (event: CustomEvent) => {
      const { datestamp, data, dataType } = event.detail
      // if there's no data, don't update
      if (Object.entries(data).length === 0) {
        return
      }
      setHasReceivedData(true)

      if (data.error) {
        setError(data.error)
      }

      // Before clearing metadata on day rollover, preserve the last metadata row
      if (datestamp && datestamp !== date) {
        if (Object.keys(metadata).length > 0) {
          const lastSeq = Object.keys(metadata)
            .map(Number)
            .sort((a, b) => a - b)
            .pop()

          if (lastSeq !== undefined) {
            const lastRow = metadata[lastSeq]
            if (lastRow && "Date begin" in lastRow) {
              setLastKnownMetadataRow(lastRow)
            }
          }
        }

        setDateAndUpdateHeader(datestamp)
        setMetadata({})
        setChannelData({})
      }

      if (dataType === "metadata") {
        setMetadata(data)
        setLastKnownMetadataRow(undefined)
      } else if (dataType === "channelData") {
        setChannelData(data)
      }
    },
    [date, metadata]
  )

  useEffect(() => {
    window.addEventListener("camera", handleCameraEvent as EL)
    return () => {
      window.removeEventListener("camera", handleCameraEvent as EL)
    }
  }, [handleCameraEvent])

  useEffect(() => {
    window.addEventListener(
      "historicalDataUpdate",
      handleHistoricalDataUpdate as EL
    )
    function handleHistoricalDataUpdate(event: CustomEvent) {
      const { data, dataType } = event.detail
      if (data.date !== date) {
        return
      }
      if (dataType === "historicalStructuredData") {
        console.log(
          "Received historical structured data update for date:",
          data.date
        )
        const channelData = createTableFromStructuredData(
          camera.name,
          data.date,
          data.structuredData,
          data.extensionInfo,
          camera.channels
        )
        setChannelData(channelData)
      } else if (dataType === "historicalMetadata") {
        console.log("Received historical metadata update for date:", data.date)
        setMetadata(data.metadata)
      }
    }
    return () => {
      window.removeEventListener(
        "historicalDataUpdate",
        handleHistoricalDataUpdate as EL
      )
    }
  }, [date, camera.name, camera.channels])

  if (unfilteredRowsCount == 0 && hasReceivedData) {
    return <h3>There is no data for this day</h3>
  } else if (!hasReceivedData) {
    const colours = camera.channels.map((c) => c.colour)
    return (
      <div className="loading-container">
        <LoadingBar colours={colours} />
        <h3>Loading data for {date}...</h3>
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

  const displayReadyClass = isReadyToDisplay ? "opaque" : "transparent"
  const tableHeaderClass = `table-header row ${displayReadyClass} transition-opacity`

  return (
    <RubinTVTableContext.Provider
      value={{ siteLocation, locationName, camera, dayObs: date }}
    >
      <div className="table-container">
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
            <div className={tableHeaderClass}>
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
