import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import {
  cameraType,
  eventType,
  metadataType,
  mosaicSingleView,
} from "./componentPropTypes"

const commonColumns = ["seqNum"]

export default function MosaicView({ locationName, camera }) {
  const [historicalBusy, setHistoricalBusy] = useState(null)
  const [currentMeta, setCurrentMeta] = useState({})
  const initialViews = camera.mosaic_view_meta.map((view) => ({
    ...view,
    latestEvent: {},
  }))
  const [views, setViews] = useState(initialViews)


  useEffect(() => {
    window.addEventListener("camera", handleMetadataChange)
    window.addEventListener("historicalStatus", handleHistoricalStateChange)
    window.addEventListener("channel", handleChannelEvent)
    
    function handleMetadataChange(event) {
      const { data, dataType } = event.detail
      if (Object.entries(data).length < 1 || dataType !== "metadata") {
        return
      }
      setCurrentMeta(data)
    }

    function handleHistoricalStateChange(event) {
      const { data: historicalBusy } = event.detail
      setHistoricalBusy(historicalBusy)
    }

    function handleChannelEvent(event) {
      const { data } = event.detail
      if (!data) {
        return
      }
      const { channel_name: chanName } = data
      setViews((prevViews) =>
        prevViews.map((view) =>
          view.channel === chanName ? { ...view, latestEvent: data } : view
        )
      )
    }

    return () => {
      window.removeEventListener("camera", handleMetadataChange)
      window.removeEventListener(
        "historicalStatus",
        handleHistoricalStateChange
      )
      window.removeEventListener("channel", handleChannelEvent)
    }
  })

  return (
    <div className="viewsArea">
      <ul className="views">
        {views.map((view) => {
          return (
            <li key={view.channel} className="view">
              <ChannelView
                locationName={locationName}
                camera={camera}
                view={view}
                currentMeta={currentMeta}
              />
            </li>
          )
        })}
      </ul>
    </div>
  )
}
MosaicView.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
}

function ChannelView({ locationName, camera, view, currentMeta }) {
  const channel = camera.channels.find(({ name }) => name === view.channel)
  if (!channel) {
    return <h3>Channel {view.channel} not found</h3>
  }
  const { latestEvent: { day_obs: dayObs }} = view
  return (
    <>
      <h3 className="channel">{channel.title}
        { dayObs && (
          <span>: { dayObs }</span>
        ) }
      </h3>
      <ChannelMedia
        locationName={locationName}
        camera={camera}
        event={view.latestEvent}
      />
      <ChannelMetadata
        view={view}
        metadata={currentMeta}
      />
    </>
  )
}
ChannelView.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  view: mosaicSingleView,
  currentMeta: metadataType
}

function ChannelMedia({ locationName, camera, event }) {
  const { filename, ext } = event
  const mediaURL = buildMediaURI(locationName, camera.name, event.channel_name, filename)
  switch (ext) {
    case 'mp4':
      return <ChannelVideo mediaURL={mediaURL}/>
    case 'jpg':
    case 'jpeg':
    case 'png':
      return <ChannelImage mediaURL={mediaURL}/>
    default:
      return <ChannelMediaPlaceholder/>
  }
}
ChannelMedia.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  event: eventType,
}

function ChannelImage({mediaURL}) {
  const imgSrc = new URL(`event_image/${mediaURL}`, APP_DATA.baseUrl)
  return (
    <div className="viewImage">
      <a href={imgSrc}>
        <img className="resp" src={imgSrc} />
      </a>
    </div>
  )
}
ChannelImage.propTypes = {
  mediaURL: PropTypes.string,
}

function ChannelVideo({mediaURL}) {
  const videoSrc = new URL(`event_video/${mediaURL}`, APP_DATA.baseUrl)
  return (
    <div className="viewVideo">
      <a href={videoSrc}>
        <video className="resp" controls autoPlay loop>
          <source src={videoSrc}/>
        </video>
      </a>
    </div>
  )
}
ChannelVideo.propTypes = {
  mediaURL: PropTypes.string,
}

function ChannelMediaPlaceholder() {
  return (
    <div className="viewImage placeholder">
      <h4 className="image-placeholder">Nothing today yet</h4>
    </div>
  )
}

function ChannelMetadata({ view, metadata }) {
  const { channel, metaColumns: viewColumns, latestEvent: {seq_num: seqNum} } = view
  if (viewColumns.length == 0) {
    return
  }
  const columns = [...commonColumns, ...viewColumns]
  const metadatum = metadata[seqNum] || {}
  return (
    <table className="viewMeta" id={`table-${channel}`}>
      <tbody>
        {columns.map((column) => {
          const value = metadatum[column] ?? "No value set"
          return (
            <tr key={column} className="viewMetaCol">
              <th scope="row" className="colName">{column}</th>
              <td className="colValue">{value}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
ChannelMetadata.propTypes = {
  view: mosaicSingleView,
  metadata: metadataType,
}

const buildMediaURI = (locationName, cameraName, channelName, filename) =>
  `${locationName}/${cameraName}/${channelName}/${filename}`
