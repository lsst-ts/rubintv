import React from 'react'
import propTypes from 'prop-types'
import { indicatorForAttr, _elWithClass, _elWithAttrs } from '../modules/utils'

function formatImageLink (link, seqNum) {
  const date = window.APP_DATA.date
  const formattedLink = link
    .replace('{dayObs}', date.replaceAll('-', ''))
    .replace('{seqNum}', seqNum.padStart(6, '0'))
  return formattedLink
}

function DictMetadata ({ data, seqNum, columnName }) {
  let buttonIcon
  if ('DISPLAY_VALUE' in data) {
    buttonIcon = data.DISPLAY_VALUE
  } else {
    buttonIcon = '❓'
  }
  return (
    <button
    onClick={() => _foldoutCell(seqNum, columnName, data)}
    className='button button-table'
    data-seq = {seqNum}
    data-column = {columnName}
    data-dict = { JSON.stringify(data)}
    >
      { buttonIcon }
    </button>
  )
}
DictMetadata.propTypes = {
  data: propTypes.object,
  seqNum: propTypes.string,
  columnName: propTypes.string
}

function MetadataCell ({ data, indicator, seqNum, columnName }) {
  const className = ['grid-cell meta', indicator].join(' ')
  let toDisplay = data
  if (typeof data === 'number' && data > 0 && data % 1 !== 0) {
    toDisplay = data.toFixed(3)
  } else if (data && typeof data === 'object') {
    toDisplay = <DictMetadata data={data} seqNum={seqNum} columnName={columnName} />
  }
  return (
    <td className={ className }>
      { toDisplay }
    </td>
  )
}
MetadataCell.propTypes = {
  data: propTypes.any,
  indicator: propTypes.string,
  seqNum: propTypes.string,
  columnName: propTypes.string
}

// Component for individual channel cell
function ChannelCell ({ event, chanName }) {
  const eventURL = window.APP_DATA.eventURL
  return (
    <td className="grid-cell">
      {event && (
        <a
          className={`button button-table ${chanName}`}
          href={`${eventURL}?key=${event.key}`}
        />
      )}
    </td>
  )
}
ChannelCell.propTypes = {
  event: propTypes.object,
  chanName: propTypes.string,
  eventURL: propTypes.string
}

// Component for individual table row
function TableRow ({ seqNum, camera, channels, channelRow, metadataColumns, metadataRow }) {
  const metadataCells = metadataColumns.map(md => {
    const indicator = indicatorForAttr(metadataRow, md.name)
    return {
      key: `${seqNum}_${md.name}`,
      data: metadataRow[md.name],
      columnName: md.name,
      seqNum,
      indicator
    }
  })
  return (
    <tr>
      <td className="grid-cell seq">{seqNum}</td>
      {/* copy to clipboard and CCS viewer cells */}
      <td className='grid-cell copy-to-cb'>
        <button className='button button-table copy'></button>
      </td>
      { camera.image_viewer_link && (
        <td className='grid-cell'>
          <a
            href={formatImageLink(camera.image_viewer_link, seqNum)}
            className='button button-table image-viewer-link' />
        </td>
      )}
      {channels.map(chan => (
        <ChannelCell key={`${seqNum}_${chan.name}`} event={channelRow[chan.name]} chanName={chan.name}/>
      ))}
      {metadataCells.map(md => (
        // eslint-disable-next-line react/jsx-key
        <MetadataCell {...md} />
      ))}
    </tr>
  )
}
TableRow.propTypes = {
  seqNum: propTypes.string,
  camera: propTypes.object,
  channels: propTypes.array,
  channelRow: propTypes.object,
  metadataColumns: propTypes.array,
  metadataRow: propTypes.object
}

// Body component for rendering rows of data
function TableBody ({ camera, channels, channelData, metadataColumns, metadata }) {
  const allSeqs = Array.from(
    new Set(
      Object.keys(channelData).concat(Object.keys(metadata))
    )).map(seq => parseInt(seq))
    .toSorted((a, b) => a - b)
    .reverse()
    .map(seq => `${seq}`)
  return (
      <tbody>
      {allSeqs.map(seqNum => {
        const metadataRow = seqNum in metadata ? metadata[seqNum] : {}
        const channelRow = seqNum in channelData ? channelData[seqNum] : {}
        return (
          <TableRow key={seqNum}
            seqNum={seqNum}
            camera={camera}
            channels={channels}
            channelRow={channelRow}
            metadataColumns={metadataColumns}
            metadataRow={metadataRow}
            />
        )
      }
      )}
    </tbody>
  )
}
TableBody.propTypes = {
  camera: propTypes.object,
  channels: propTypes.array,
  metadataColumns: propTypes.array,
  channelData: propTypes.object,
  metadata: propTypes.object,
  eventURL: propTypes.string
}

// Component for individual channel header
function ChannelHeader ({ channel }) {
  const thProps = { className: 'grid-title gt-channel sideways' }
  if (channel.desc) {
    thProps.title = channel.desc
  }
  return (
    <th {...thProps}>
      {channel.label || channel.title || channel.name}
    </th>
  )
}
ChannelHeader.propTypes = {
  channel: propTypes.object
}

// Header component for rendering column titles
function TableHeader ({ camera, metadataColumns }) {
  const channelColumns = seqChannels(camera)
  const columns = channelColumns.concat(metadataColumns)
  // const columns =
  return (
    <thead>
      <tr>
        <th className="grid-title sideways">Seq. No.</th>
        <th id='ctbEmpty'></th>
        { camera.image_viewer_link && (
          <th className='grid-title sideways'>
            CCS Image Viewer
          </th>
        )}
        {columns.map(channel => (
          <ChannelHeader key={channel.name} channel={channel} />
        ))}
        {/* ... additional columns such as CCS Image Viewer if necessary ... */}
      </tr>
    </thead>
  )
}
TableHeader.propTypes = {
  camera: propTypes.object,
  metadataColumns: propTypes.array,
  selected: propTypes.array
}

export default function TableView ({ camera, channelData, metadata, metadataColumns }) {
  return (
      <table className="camera-table">
        <TableHeader camera={camera}
          metadataColumns={metadataColumns} />
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
  camera: propTypes.object,
  metadataColumns: propTypes.array,
  channelData: propTypes.object,
  metadata: propTypes.object,
  eventURL: propTypes.string
}

function seqChannels (camera) {
  return camera.channels.filter((cam) => !cam.per_day)
}

function _foldoutCell (seqNum, columnName, data) {
  const overlay = _elWithClass('div', 'full-overlay')
  overlay.id = 'overlay'
  const modal = _elWithClass('div', 'cell-dict-modal')
  const closeButton = _elWithClass('div', 'close-button')
  closeButton.textContent = 'x'
  closeButton.id = 'modal-close'
  const heading = _elWithAttrs('h3')
  heading.textContent = `Seq Num: ${seqNum} - ${columnName}`
  modal.appendChild(closeButton)
  modal.appendChild(heading)

  const table = _elWithClass('table', 'cell-dict')
  for (const [k, v] of Object.entries(data)) {
    if (k === 'DISPLAY_VALUE') {
      continue
    }
    const tRow = _elWithAttrs('tr')
    const head = _elWithAttrs('th', { class: 'key', text: k })
    const datum = _elWithAttrs('td', { class: 'value', text: v })
    tRow.appendChild(head)
    tRow.appendChild(datum)
    table.appendChild(tRow)
  }
  modal.appendChild(table)
  overlay.appendChild(modal)
  document.querySelector('main').appendChild(overlay)
  document.activeElement.blur()
  overlay.addEventListener('click', (e) => {
    if (e.target.id === 'overlay' || e.target.id === 'modal-close') {
      modal.remove()
      overlay.remove()
    }
  })
  document.body.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      modal.remove()
      overlay.remove()
    }
  })
}
