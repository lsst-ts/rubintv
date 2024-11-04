import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import {
  cameraType,
  eventType,
  metadataType,
  mosaicSingleView,
} from "./componentPropTypes"
import { _getById, addStrHashCode } from "../modules/utils"

const FRAMELENGTH = 0.1
const BACK = -FRAMELENGTH
const FORWARD = FRAMELENGTH

// add hashing method to String prototype
addStrHashCode()

const commonColumns = ["seqNum"]

export default function MosaicView({ locationName, camera }) {
  const [historicalBusy, setHistoricalBusy] = useState(null)
  const [currentMeta, setCurrentMeta] = useState({})
  const isFocusable = checkNeedsFocusability()
  const [views, setViews] = useState(initialViews)

  function initialViews() {
    const views = camera.mosaic_view_meta.map((view, index) => ({
      ...view,
      latestEvent: {},
      hasFocus: index == 0 ? true : false,
    }))
    return views
  }

  function checkNeedsFocusability() {
    // Is there more than one video?
    const vids = camera.mosaic_view_meta.filter(
      ({ mediaType }) => mediaType === "image"
    )
    return vids.length > 1 ? true : false
  }

  function setHasFocus(thisView) {
    setViews((prevViews) =>
      prevViews.map((view) =>
        view.channel === thisView.channel
          ? { ...view, hasFocus: true }
          : { ...view, hasFocus: false }
      )
    )
  }

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
  }, [])

  return (
    <div className="viewsArea">
      <ul className="views">
        {views.map((view) => {
          return (
            <ChannelView
              locationName={locationName}
              camera={camera}
              view={view}
              currentMeta={currentMeta}
              setHasFocus={setHasFocus}
              isFocusable={isFocusable}
              key={view.channel}
            />
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

function ChannelView({
  locationName,
  camera,
  view,
  currentMeta,
  setHasFocus,
  isFocusable,
}) {
  const channel = camera.channels.find(({ name }) => name === view.channel)
  if (!channel) {
    return <h3>Channel {view.channel} not found</h3>
  }
  const {
    hasFocus,
    mediaType,
    latestEvent: { day_obs: dayObs },
  } = view
  const clsName = ["view", `view-${mediaType}`, hasFocus ? "has-focus" : null]
    .join(" ")
    .trimEnd()
  const clickHandler = isFocusable ? () => setHasFocus(view) : null
  return (
    <li className={clsName} onClick={clickHandler}>
      <h3 className="channel">
        {channel.title}
        {dayObs && <span>: {dayObs}</span>}
      </h3>
      <ChannelMedia
        locationName={locationName}
        camera={camera}
        event={view.latestEvent}
        mediaType={mediaType}
      />
      <ChannelMetadata view={view} metadata={currentMeta} />
    </li>
  )
}
ChannelView.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  view: mosaicSingleView,
  currentMeta: metadataType,
}

function ChannelMedia({ locationName, camera, event, mediaType }) {
  const { filename } = event
  if (!filename) return <ChannelMediaPlaceholder />
  const mediaURL = buildMediaURI(
    locationName,
    camera.name,
    event.channel_name,
    filename
  )
  switch (mediaType) {
    case "video":
      return <ChannelVideo mediaURL={mediaURL} />
    case "image":
    default:
      return <ChannelImage mediaURL={mediaURL} />
  }
}
ChannelMedia.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  event: eventType,
  mediaType: PropTypes.string,
}

function ChannelImage({ mediaURL }) {
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

function ChannelVideo({ mediaURL }) {
  const [isLoaded, setIsLoaded] = useState(false)

  const videoSrc = new URL(`event_video/${mediaURL}`, APP_DATA.baseUrl)
  const vidID = `v_${mediaURL.hashCode()}`
  return (
    <div className="viewVideo">
      <a href={videoSrc}>
        <video className="resp" id={vidID} autoPlay loop controls onLoadedData={() => setIsLoaded(true)}>
          <source src={videoSrc} />
        </video>
      </a>
      { isLoaded && (
        <div className="video-extra-controls">
          <button onClick={() => frameStep(vidID, BACK)}>&lt;</button>
          <button onClick={() => frameStep(vidID, FORWARD)}>&gt;</button>
        </div>
      )
      }
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
  const {
    channel,
    metaColumns: viewColumns,
    latestEvent: { seq_num: seqNum },
  } = view
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
              <th scope="row" className="colName">
                {column}
              </th>
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

function frameStep(vidID, timeDelta) {
  console.log('frame delta is: ',timeDelta)
  const video = _getById(vidID)
  pauseVideo(video)
  if (timeDelta < 0 && video.currentTime < 0) {
    video.currentTime = 0
  } else if (timeDelta > 0 && video.currentTime > video.duration) {
    video.currentTime = video.duration
  } else {
    video.currentTime = video.currentTime + timeDelta
  }
}

window.onkeydown = videoControl

function videoControl(e) {
  const video = document.querySelector(".view-video.has-focus video")
  if (!video) {
    return
  }
  const key = e.code
  let timeDelta = 0
  switch(key) {
    case "ArrowLeft":
      timeDelta = BACK
      break
    case "ArrowRight":
      timeDelta = FORWARD
  }
  if (timeDelta) {
    frameStep(video.id, timeDelta)
  }
}

function pauseVideo(video) {
  if (!video.isPaused) {
    video.pause()
  }
}
