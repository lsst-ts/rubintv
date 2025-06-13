import React, { useContext } from "react"
import { FilterDialog } from "./TableFilter"
import { useModal } from "./Modal"
import {
  indicatorForAttr,
  _elWithAttrs,
  replaceInString,
  _getById,
  setCameraBaseUrl,
} from "../modules/utils"
import {
  MetadatumType,
  ChannelData,
  ExposureEvent,
  TableContext,
  TableContextType,
  Channel,
  Camera,
  Metadata,
  MetadataRow,
  MetadataColumn,
  SortingOptions,
  FilterOptions,
} from "./componentTypes"
import { get } from "http"

// TODO: this should be set in the backend
// See DM-50192
const hasCCS = (siteLoc: string) => {
  return ["summit", "base"].includes(siteLoc)
}

function MetadataCell({
  data,
  indicator,
  seqNum,
  columnName,
}: {
  data: MetadatumType
  indicator: string
  seqNum: string
  columnName: string
}) {
  let toDisplay: string | React.ReactElement = ""
  let title = ""
  const className = ["grid-cell meta", indicator].join(" ")
  if (typeof data === "number" && data % 1 !== 0) {
    toDisplay = data.toFixed(2)
    title = data.toString()
  } else if (typeof data === "boolean") {
    toDisplay = data ? "True" : "False"
  } else if (data && typeof data === "object") {
    toDisplay = (
      <FoldoutCell data={data} seqNum={seqNum} columnName={columnName} />
    )
  }
  return (
    <td className={className} title={title}>
      {toDisplay}
    </td>
  )
}

// Component for individual channel cell
function ChannelCell({
  event,
  chanName,
  chanColour,
  noEventReplacement,
}: {
  event?: ExposureEvent
  chanName: string
  chanColour: string
  noEventReplacement?: string
}) {
  const { locationName, camera } = useContext(TableContext) as TableContextType
  const { getEventUrl } = setCameraBaseUrl(locationName, camera.name)
  return (
    <td className="grid-cell">
      {event && (
        <a
          className={`button button-table ${chanName}`}
          style={{ backgroundColor: chanColour }}
          href={getEventUrl(event)}
          aria-label={chanName}
        ></a>
      )}
      {!event && noEventReplacement && (
        <p className="center-text cell-emoji">{noEventReplacement}</p>
      )}
    </td>
  )
}

// Component for individual table row
function TableRow({
  seqNum,
  camera,
  channels,
  channelRow,
  metadataColumns,
  metadataRow,
}: {
  seqNum: string
  camera: Camera
  channels: Channel[]
  channelRow: Record<string, ExposureEvent>
  metadataColumns: MetadataColumn[]
  metadataRow: MetadataRow
}) {
  const { dayObs, siteLocation } = useContext(TableContext) as TableContextType
  const siteLocHasCCS = hasCCS(siteLocation)

  // Entries in metadata keyed `"@{channel_name}"` will have their
  // values show up in the table instead of a blank space.
  const noEventReplacements = (() => {
    const replacements = channels.reduce((obj, chan) => {
      const chanReplace = metadataRow["@" + chan.name] as string | undefined
      if (chanReplace != null) {
        obj[chan.name] = chanReplace
      }
      return obj
    }, {} as Record<string, string>)
    // Only return if there is at least one replacement
    return Object.keys(replacements).length > 0 ? replacements : undefined
  })()

  const metadataCells = metadataColumns.map((md) => {
    const indicator = indicatorForAttr(metadataRow, md.name)
    return {
      data: metadataRow[md.name],
      columnName: md.name,
      seqNum,
      indicator,
    }
  })

  // If this row of metadata contains a value for the
  // channel name "controller", then extract that value
  const controller = metadataRow["controller"]
    ? (metadataRow["controller"] as string)
    : undefined

  return (
    <tr>
      <td className="grid-cell seq" id={`seqNum-${seqNum}`}>
        {seqNum}
      </td>
      {/* copy to clipboard and CCS viewer cells */}
      {camera.copy_row_template && (
        <td className="grid-cell copy-to-cb">
          <button
            className="button button-table copy"
            onClick={(e) => {
              handleCopyButton(dayObs, seqNum, camera.copy_row_template!, e)
            }}
          ></button>
        </td>
      )}
      {camera.image_viewer_link && siteLocHasCCS && (
        <td className="grid-cell">
          <a
            href={replaceInString(camera.image_viewer_link, dayObs, seqNum, {
              siteLocation: siteLocation,
              controller: controller,
            })}
            className="button button-table image-viewer-link"
          />
        </td>
      )}
      {channels.map((chan) => (
        <ChannelCell
          key={`${seqNum}_${chan.name}`}
          event={channelRow[chan.name]}
          chanName={chan.name}
          chanColour={chan.colour}
          noEventReplacement={noEventReplacements?.[chan.name]}
        />
      ))}
      {metadataCells.map((md) => (
        <MetadataCell {...md} key={`${seqNum}_${md.columnName}`} />
      ))}
    </tr>
  )
}

// Body component for rendering rows of data
function TableBody({
  camera,
  channels,
  channelData,
  metadataColumns,
  metadata,
  sortOn,
}: {
  camera: Camera
  channels: Channel[]
  channelData: ChannelData
  metadataColumns: MetadataColumn[]
  metadata: Metadata
  sortOn: SortingOptions
}) {
  const allSeqs = Array.from(
    new Set(Object.keys(channelData).concat(Object.keys(metadata)))
  )
  const seqs = applySorting(allSeqs, sortOn, metadata, channelData)
  return (
    <tbody>
      {seqs.map((seqNum) => {
        const metadataRow = seqNum in metadata ? metadata[seqNum] : {}
        const channelRow = seqNum in channelData ? channelData[seqNum] : {}
        return (
          <TableRow
            key={seqNum}
            seqNum={seqNum.toString()}
            camera={camera}
            channels={channels}
            channelRow={channelRow}
            metadataColumns={metadataColumns}
            metadataRow={metadataRow}
          />
        )
      })}
    </tbody>
  )
}

// Function to sort the rows based on the selected column
// and order (ascending or descending)
function applySorting(
  allSeqs: string[],
  sortOn: SortingOptions,
  metadata: Metadata,
  channelData: ChannelData
) {
  const getValue = (seq: number) =>
    metadata[seq]?.[sortOn.column] ?? channelData[seq]?.[sortOn.column]

  const compare = (a: number, b: number) => {
    if (sortOn.column === "seq") {
      return sortOn.order === "asc" ? a - b : b - a
    }
    const aValue = getValue(a)
    const bValue = getValue(b)

    // Both strings
    if (typeof aValue === "string" && typeof bValue === "string") {
      if (aValue === bValue) return sortOn.order === "asc" ? a - b : b - a
      return sortOn.order === "asc"
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }

    // If either is undefined or not a number, fallback to seq
    if (
      aValue === undefined ||
      bValue === undefined ||
      typeof aValue !== "number" ||
      typeof bValue !== "number"
    ) {
      return sortOn.order === "asc" ? a - b : b - a
    }

    // Both numbers (or booleans)
    return sortOn.order === "asc" ? aValue - bValue : bValue - aValue
  }

  return allSeqs.slice().map(Number).sort(compare)
}

// Component for individual channel header
function ChannelHeader({
  channel,
  filterOn,
  setFilterOn,
  filteredRowsCount,
  unfilteredRowsCount,
  sortOn,
  setSortOn,
}: {
  channel: Channel | MetadataColumn
  filterOn: FilterOptions
  setFilterOn: (filter: FilterOptions) => void
  filteredRowsCount: number
  unfilteredRowsCount: number
  sortOn: SortingOptions
  setSortOn: React.Dispatch<React.SetStateAction<SortingOptions>>
}) {
  const { showModal } = useModal()

  const handleColumnClick = (event: React.MouseEvent, column: string) => {
    handleSortClick(event, column, setSortOn)
    if (!event.shiftKey) {
      showModal(
        <FilterDialog
          column={channel.name}
          setFilterOn={setFilterOn}
          filterOn={filterOn}
          filteredRowsCount={filteredRowsCount}
          unfilteredRowsCount={unfilteredRowsCount}
        />
      )
    }
  }

  const isMetadataColumn = !channel.hasOwnProperty("title")
  const containerClass = isMetadataColumn
    ? "meta grid-title sortable"
    : "grid-title"
  const isFilteredOn = filterOn.column === channel.name && filterOn.value !== ""
  const titleClass = isFilteredOn ? "filtering sideways" : "sideways"
  const isSortedOn = sortOn.column === channel.name
  const sortingClass = `sorting-indicator ${sortOn.order}`

  const containerProps = {
    className: containerClass,
  } as React.PropsWithoutRef<React.HTMLAttributes<HTMLDivElement>>
  if (isMetadataColumn) {
    containerProps.onClick = (event) => handleColumnClick(event, channel.name)
    containerProps.title = (channel as MetadataColumn).desc
  }
  const label =
    (channel as Channel).label ||
    (channel as Channel).title ||
    (channel as MetadataColumn).name
  return (
    <div {...containerProps}>
      {isSortedOn && <div className={sortingClass}></div>}
      <div className={titleClass}>{label}</div>
    </div>
  )
}

// Header component for rendering column titles
export function TableHeader({
  camera,
  metadataColumns,
  filterOn,
  setFilterOn,
  filteredRowsCount,
  unfilteredRowsCount,
  sortOn,
  setSortOn,
}: {
  camera: Camera
  metadataColumns: MetadataColumn[]
  filterOn: FilterOptions
  setFilterOn: (filter: FilterOptions) => void
  filteredRowsCount: number
  unfilteredRowsCount: number
  sortOn: SortingOptions
  setSortOn: React.Dispatch<React.SetStateAction<SortingOptions>>
}) {
  const { siteLocation } = useContext(TableContext) as TableContextType
  const siteLocHasCCS = hasCCS(siteLocation)
  const channelColumns = seqChannels(camera) as (Channel | MetadataColumn)[]
  const columns = channelColumns.concat(metadataColumns)
  const sorting = sortOn.column == "seq"
  const sortingClass = `sorting-indicator ${sortOn.order}`
  return (
    <>
      <div
        className="grid-title sortable"
        onClick={(event) => handleSortClick(event, "seq", setSortOn)}
      >
        {sorting && <div className={sortingClass}></div>}
        <div className="sideways">Seq. No.</div>
      </div>
      {camera.copy_row_template && (
        <div className="grid-title" id="ctbEmpty"></div>
      )}
      {camera.image_viewer_link && siteLocHasCCS && (
        <div className="grid-title sideways">CCS Image Viewer</div>
      )}
      {columns.map((channel) => {
        return (
          <ChannelHeader
            key={channel.name}
            channel={channel}
            filterOn={filterOn}
            setFilterOn={setFilterOn}
            filteredRowsCount={filteredRowsCount}
            unfilteredRowsCount={unfilteredRowsCount}
            sortOn={sortOn}
            setSortOn={setSortOn}
          />
        )
      })}
    </>
  )
}

export default function TableView({
  camera,
  channelData,
  metadata,
  metadataColumns,
  filterOn,
  filteredRowsCount,
  sortOn,
  siteLocation,
}: {
  camera: Camera
  channelData: ChannelData
  metadata: Metadata
  metadataColumns: MetadataColumn[]
  filterOn: FilterOptions
  filteredRowsCount: number
  sortOn: SortingOptions
  siteLocation: string
}) {
  const filterColumnSet = filterOn.column !== "" && filterOn.value !== ""
  if (filterColumnSet && filteredRowsCount == 0) {
    return (
      <h3 className="center-text" style={{ marginTop: "1em" }}>
        There are no rows for &quot;{filterOn.value}&quot; in {filterOn.column}
      </h3>
    )
  }
  return (
    <table className="camera-table">
      <TableBody
        camera={camera}
        channels={seqChannels(camera)}
        channelData={channelData}
        metadataColumns={metadataColumns}
        metadata={metadata}
        sortOn={sortOn}
      />
    </table>
  )
}

function seqChannels(camera: Camera): Channel[] {
  return camera.channels.filter((cam) => !cam.per_day)
}

/** Generate a modal window for displaying a metadata object of
 * key/value pairs. The function is called when button in a metadata cell of
 * the table is clicked.
 */
function FoldoutCell({
  seqNum,
  columnName,
  data,
}: {
  seqNum: string
  columnName: string
  data: MetadatumType | Record<string, any>
}) {
  if (!data || typeof data !== "object") {
    return null
  }
  const { showModal } = useModal()

  let toDisplay: string = ""
  if (Array.isArray(data)) {
    // If data is an array, we can display it as a list
    toDisplay = "📖"
  } else {
    toDisplay = data.hasOwnProperty("DISPLAY_VALUE")
      ? data["DISPLAY_VALUE"]
      : "📖"
  }

  const handleClick = () => {
    const content = (
      <div className="cell-dict-modal">
        <div className="modal-header">
          <h3>{`Seq Num: ${seqNum} - ${columnName}`}</h3>
        </div>
        <table className="cell-dict">
          <tbody>
            {Object.entries(data).map(
              ([key, value]) =>
                key !== "DISPLAY_VALUE" && (
                  <tr key={key}>
                    <th className="key">{key}</th>
                    <td className="value">{value}</td>
                  </tr>
                )
            )}
          </tbody>
        </table>
      </div>
    )
    showModal(content)
  }
  return (
    <button onClick={handleClick} className="button button-table">
      {toDisplay}
    </button>
  )
}

function handleCopyButton(
  date: string,
  seqNum: string,
  template: string,
  event: React.MouseEvent
) {
  const dayObs = date.replace(/-/g, "")
  const dataStr = replaceInString(template, dayObs, seqNum)
  navigator.clipboard.writeText(dataStr)
  const responseMsg = _elWithAttrs("div", {
    class: "copied",
    text: `DataId for ${seqNum} copied to clipboard`,
  })
  const callingElement = event.currentTarget as HTMLElement
  const pos = callingElement.getBoundingClientRect()
  responseMsg.setAttribute(
    "style",
    `top: ${pos.y - pos.height / 2}px; left: ${pos.x + (pos.width + 8)}px`
  )
  responseMsg.addEventListener("animationend", () => {
    responseMsg.remove()
  })
  document.body.append(responseMsg)
}

export { TableRow }

const handleSortClick = (
  event: React.MouseEvent,
  column: string,
  setSortOn: React.Dispatch<React.SetStateAction<SortingOptions>>
) => {
  event.stopPropagation()
  const isShiftKey = event.shiftKey
  if (isShiftKey) {
    // if shift key pressed, use this column
    // for sorting
    setSortOn((prev: SortingOptions) => {
      if (prev.column === column) {
        return {
          column: column,
          order: prev.order === "asc" ? "desc" : "asc",
        }
      }
      return {
        column: column,
        order: "asc",
      }
    })
  }
}
