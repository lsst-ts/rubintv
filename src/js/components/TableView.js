import React from "react"
import PropTypes from "prop-types"
import { FilterDialog } from "./TableFilter"
import { useModal } from "./Modal"
import {
  indicatorForAttr,
  _elWithAttrs,
  replaceInString,
  _getById,
} from "../modules/utils"
import { metadatumType } from "./componentPropTypes"

// get the site location from the global APP_DATA object
// which is set in the template
const siteLoc = window.APP_DATA.siteLocation
// TODO: this should be set in the backend
// See DM-50192
const hasCCS = (siteLoc) => {
  return ["summit", "base"].includes(siteLoc)
}
const siteLocHasCCS = hasCCS(siteLoc)

function DictMetadata({ data, seqNum, columnName }) {
  if (typeof data !== "object" || data === null) {
    return null
  }
  return <FoldoutCell seqNum={seqNum} columnName={columnName} data={data} />
}
DictMetadata.propTypes = {
  data: PropTypes.object,
  seqNum: PropTypes.string,
  columnName: PropTypes.string,
}

function MetadataCell({ data, indicator, seqNum, columnName }) {
  const className = ["grid-cell meta", indicator].join(" ")
  let toDisplay = data
  let title = ""
  if (typeof data === "number" && data % 1 !== 0) {
    toDisplay = data.toFixed(2)
    title = data
  } else if (typeof data === "boolean") {
    toDisplay = data ? "True" : "False"
  } else if (data && typeof data === "object") {
    toDisplay = (
      <DictMetadata data={data} seqNum={seqNum} columnName={columnName} />
    )
  }
  return (
    <td className={className} title={title}>
      {toDisplay}
    </td>
  )
}
MetadataCell.propTypes = {
  data: metadatumType,
  indicator: PropTypes.string,
  seqNum: PropTypes.string,
  columnName: PropTypes.string,
}

// Component for individual channel cell
function ChannelCell({ event, chanName, chanColour, noEventReplacement }) {
  const eventUrl = window.APP_DATA.eventUrl
  return (
    <td className="grid-cell">
      {event && (
        <a
          className={`button button-table ${chanName}`}
          style={{ backgroundColor: chanColour }}
          href={`${eventUrl}?key=${event.key}`}
          aria-label={chanName} // Add accessible name
        ></a>
      )}
      {!event && noEventReplacement && (
        <p className="center-text cell-emoji">{noEventReplacement}</p>
      )}
    </td>
  )
}
ChannelCell.propTypes = {
  event: PropTypes.object,
  eventUrl: PropTypes.string,
  chanName: PropTypes.string,
  chanColour: PropTypes.string,
  noEventReplacement: PropTypes.string,
}

// Component for individual table row
function TableRow({
  seqNum,
  camera,
  channels,
  channelRow,
  metadataColumns,
  metadataRow,
}) {
  const dayObs = window.APP_DATA.date.replaceAll("-", "")

  // Entries in metadata keyed `"@{channel_name}"` will have their
  // values show up in the table instead of a blank space.
  const noEventReplacements = channels.reduce((obj, chan) => {
    const chanReplace = metadataRow["@" + chan.name] ?? null
    return { ...obj, [chan.name]: chanReplace }
  }, {})

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
    ? metadataRow["controller"]
    : null

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
            onClick={() =>
              handleCopyButton(dayObs, seqNum, camera.copy_row_template, this)
            }
          ></button>
        </td>
      )}
      {camera.image_viewer_link && siteLocHasCCS && (
        <td className="grid-cell">
          <a
            href={replaceInString(camera.image_viewer_link, dayObs, seqNum, {
              siteLoc: siteLoc,
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
          noEventReplacement={noEventReplacements[chan.name]}
        />
      ))}
      {metadataCells.map((md) => (
        <MetadataCell {...md} key={`${seqNum}_${md.columnName}`} />
      ))}
    </tr>
  )
}
TableRow.propTypes = {
  seqNum: PropTypes.string,
  camera: PropTypes.object,
  channels: PropTypes.array,
  channelRow: PropTypes.object,
  metadataColumns: PropTypes.array,
  metadataRow: PropTypes.object,
}

// Body component for rendering rows of data
function TableBody({
  camera,
  channels,
  channelData,
  metadataColumns,
  metadata,
  sortOn,
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
            seqNum={seqNum}
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
TableBody.propTypes = {
  camera: PropTypes.object,
  channels: PropTypes.array,
  metadataColumns: PropTypes.array,
  channelData: PropTypes.object,
  metadata: PropTypes.object,
  eventUrl: PropTypes.string,
}

// Function to sort the rows based on the selected column
// and order (ascending or descending)
function applySorting(allSeqs, sortOn, metadata, channelData) {
  return allSeqs.toSorted((a, b) => {
    if (sortOn.column === "seq") {
      return sortOn.order === "asc" ? a - b : b - a
    }
    const aValue =
      metadata[a]?.[sortOn.column] ?? channelData[a]?.[sortOn.column]
    const bValue =
      metadata[b]?.[sortOn.column] ?? channelData[b]?.[sortOn.column]
    if (typeof aValue === "string" && typeof bValue === "string") {
      if (aValue === bValue) {
        // if the compare values are equal, sort by seqNum
        return sortOn.order === "asc" ? a - b : b - a
      }
      return sortOn.order === "asc"
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }
    if (aValue === undefined || bValue === undefined) {
      // if one of the values is undefined, sort by seqNum
      return sortOn.order === "asc" ? a - b : b - a
    }
    return sortOn.order === "asc" ? aValue - bValue : bValue - aValue
  })
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
}) {
  const { showModal } = useModal()

  const handleColumnClick = (event, column) => {
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
  let titleClass = isFilteredOn ? "filtering sideways" : "sideways"
  const isSortedOn = sortOn.column === channel.name
  const sortingClass = `sorting-indicator ${sortOn.order}`

  const containerProps = {
    className: containerClass,
  }
  if (isMetadataColumn) {
    containerProps.onClick = () => handleColumnClick(event, channel.name)
  }
  if (channel.desc) {
    containerProps.title = channel.desc
  }
  return (
    <div {...containerProps}>
      {isSortedOn && <div className={sortingClass}></div>}
      <div className={titleClass}>
        {channel.label || channel.title || channel.name}
      </div>
    </div>
  )
}
ChannelHeader.propTypes = {
  channel: PropTypes.object,
  filterOn: PropTypes.object,
  setFilterOn: PropTypes.func,
  filteredRowsCount: PropTypes.number,
  unfilteredRowsCount: PropTypes.number,
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
}) {
  const channelColumns = seqChannels(camera)
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
TableHeader.propTypes = {
  camera: PropTypes.object,
  metadataColumns: PropTypes.array,
  filterOn: PropTypes.object,
  setFilterOn: PropTypes.func,
  filteredRowsCount: PropTypes.number,
  unfilteredRowsCount: PropTypes.number,
}

export default function TableView({
  camera,
  channelData,
  metadata,
  metadataColumns,
  filterOn,
  filteredRowsCount,
  sortOn,
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
TableView.propTypes = {
  camera: PropTypes.object,
  metadataColumns: PropTypes.array,
  channelData: PropTypes.object,
  metadata: PropTypes.object,
  filterOn: PropTypes.object,
  filteredRowsCount: PropTypes.number,
}

function seqChannels(camera) {
  return camera.channels.filter((cam) => !cam.perDay)
}

/** Generate a modal window for displaying a metadata object of
 * key/value pairs. The function is called when button in a metadata cell of
 * the table is clicked.
 */

function FoldoutCell({ seqNum, columnName, data }) {
  const { showModal } = useModal()
  const toDisplay = data.DISPLAY_VALUE
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
FoldoutCell.propTypes = {
  seqNum: PropTypes.string,
  columnName: PropTypes.string,
  data: PropTypes.object,
}

function handleCopyButton(date, seqNum, template) {
  const dayObs = date.replaceAll("-", "")
  const dataStr = replaceInString(template, dayObs, seqNum)
  navigator.clipboard.writeText(dataStr)
  const responseMsg = _elWithAttrs("div", {
    class: "copied",
    text: `DataId for ${seqNum} copied to clipboard`,
  })
  const pos = _getById(`seqNum-${seqNum}`).getBoundingClientRect()
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

const handleSortClick = (event, column, setSortOn) => {
  event.stopPropagation()
  const isShiftKey = event.shiftKey
  if (isShiftKey) {
    // if shift key pressed, use this column
    // for sorting
    setSortOn((prev) => {
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
