import React from 'react'
import propTypes from 'prop-types'
import { indicatorForAttr } from '../modules/utils'

function formatImageLink (link, seqNum) {
  const date = window.APP_DATA.date
  const formattedLink = link
    .replace('{dayObs}', date.replaceAll('-', ''))
    .replace('{seqNum}', seqNum.padStart(6, '0'))
  return formattedLink
}

function MetadataCell ({ data, indicator }) {
  const className = ['grid-cell meta', indicator].join(' ')
  return (
    <td className={ className }>
      { data &&
          typeof (data) === 'number' && data > 0
        ? data.toFixed(3)
        : data
      }
    </td>
  )
}
MetadataCell.propTypes = {
  data: propTypes.any,
  indicator: propTypes.string
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
      indicator
    }
  })
  return (
    <tr>
      <td className="grid-cell seq">{seqNum}</td>
      {/* copy to cliipboard and CCS viewer cells */}
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
    )).reverse()
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
      {channel.label || channel.title}
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

function SimpleTableView ({ camera, channelData, metadata, metadataColumns }) {
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
SimpleTableView.propTypes = {
  camera: propTypes.object,
  metadataColumns: propTypes.array,
  channelData: propTypes.object,
  metadata: propTypes.object,
  eventURL: propTypes.string
}

export default function TableApp ({ camera, date, channelData, metadata }) {
  const initialSelected = Object.keys(camera.metadata_cols)
  // const [selected, setSelected] = useState(initialSelected)
  // convert metadata_cols into array of objects
  const metadataColumns = Object.entries(camera.metadata_cols)
    .map(([title, desc]) => { return { title, desc, name: title } })
  const selectedMetaCols = metadataColumns.filter(col => initialSelected.includes(col.name))

  return (
    <div className="table-container">
      <div className="above-table-sticky">
        <h3 id="the-date">Data for day: <span className="date">{date}</span></h3>
        {/* ... other controls ... */}
      </div>
        <SimpleTableView
          camera={camera}
          channelData={channelData}
          metadata={metadata}
          metadataColumns={selectedMetaCols}
          />
    </div>
  )
}
TableApp.propTypes = {
  camera: propTypes.object,
  date: propTypes.string,
  channelData: propTypes.object,
  metadata: propTypes.object
}

function seqChannels (camera) {
  return camera.channels.filter((cam) => !cam.per_day)
}
