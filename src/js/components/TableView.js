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
  const eventURL = window.APP_DATA.eventURL
  return (
    <td className="grid-cell">
      {event && (
        <a
          className={`button button-table ${chanName}`}
          style={{ backgroundColor: chanColour }}
          href={`${eventURL}?key=${event.key}`}
        />
      )}
      {!event && noEventReplacement && (
        <p className="center-text cell-emoji">{noEventReplacement}</p>
      )}
    </td>
  )
}
ChannelCell.propTypes = {
  event: PropTypes.object,
  eventURL: PropTypes.string,
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
      {camera.image_viewer_link && (
        <td className="grid-cell">
          <a
            href={replaceInString(camera.image_viewer_link, dayObs, seqNum)}
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
}) {
  const allSeqs = Array.from(
    new Set(Object.keys(channelData).concat(Object.keys(metadata)))
  )
    .map((seq) => parseInt(seq))
    .toSorted((a, b) => a - b)
    .reverse()
    .map((seq) => `${seq}`)
  return (
    <tbody>
      {allSeqs.map((seqNum) => {
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
  eventURL: PropTypes.string,
}

// Component for individual channel header
function ChannelHeader({
  channel,
  filterOn,
  setFilterOn,
  filteredRowsCount,
  unfilteredRowsCount,
}) {
  const { showModal } = useModal()
  const filterClass =
    channel.name === filterOn.column && filterOn.value !== "" ? "filtering" : ""

  const handleColumnClick = () => {
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
  const elProps = {
    className: `grid-title gt-channel sideways ${filterClass}`,
    onClick: handleColumnClick,
  }
  if (channel.desc) {
    elProps.title = channel.desc
  }
  return (
    <div {...elProps}>{channel.label || channel.title || channel.name}</div>
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
}) {
  const channelColumns = seqChannels(camera)
  const columns = channelColumns.concat(metadataColumns)
  return (
    <>
      <div className="grid-title sideways">Seq. No.</div>
      {camera.copy_row_template && (
        <div className="grid-title" id="ctbEmpty"></div>
      )}
      {camera.image_viewer_link && (
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
  return camera.channels.filter((cam) => !cam.per_day)
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
