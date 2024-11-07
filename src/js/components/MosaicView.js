import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import {
  cameraType,
  eventType,
  metadataType,
  mosaicSingleView,
} from "./componentPropTypes"
import { _getById, getStrHashCode } from "../modules/utils"

const FRAMELENGTH = 0.1
const BACK = -FRAMELENGTH
const FORWARD = FRAMELENGTH

class MediaType {
  static IMAGE = { value: "image" }
  static VIDEO = { value: "video" }

  static getMediaType(type) {
    switch (type) {
      case "image":
        return this.IMAGE
      case "video":
        return this.VIDEO
      default:
        return null
    }
  }
}

const commonColumns = ["seqNum"]

export default function MosaicView({ locationName, camera }) {
  const [historicalBusy, setHistoricalBusy] = useState(null)
  const [currentMeta, setCurrentMeta] = useState({})
  const [views, setViews] = useState(initialViews)

  function initialViews() {
    let videoCount = 0
    const views = camera.mosaic_view_meta.map((view) => {
      const isVideo = view.mediaType === MediaType.VIDEO.value
      videoCount += isVideo ? 1 : 0
      return {
        ...view,
        mediaType: MediaType.getMediaType(view.mediaType),
        latestEvent: {},
        // only apply 'selected == true' to first video
        selected: isVideo && videoCount == 1 ? true : false,
      }
    })
    return views
  }

  function hasMultipleVideos() {
    // Is there more than one video?
    const vids = camera.mosaic_view_meta.filter(
      ({ mediaType }) => mediaType === MediaType.VIDEO
    )
    return vids.length > 1 ? true : false
  }

  function selectView(thisView) {
    setViews((prevViews) =>
      prevViews.map((view) =>
        view.channel === thisView.channel
          ? { ...view, selected: true }
          : { ...view, selected: false }
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
            <ChannelViewListItem
              locationName={locationName}
              camera={camera}
              view={view}
              currentMeta={currentMeta}
              selectView={selectView}
              isSelectable={hasMultipleVideos()}
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

function ChannelViewListItem({
  locationName,
  camera,
  view,
  currentMeta,
  selectView,
  isSelectable,
}) {
  const channel = camera.channels.find(({ name }) => name === view.channel)
  if (!channel) {
    return <h3>Channel {view.channel} not found</h3>
  }
  const {
    selected,
    mediaType,
    latestEvent: { day_obs: dayObs },
  } = view
  const clsName = [
    "view",
    `view-${mediaType.value}`,
    selected ? "selected" : null,
  ]
    .join(" ")
    .trimEnd()
  const clickHandler = isSelectable ? () => selectView(view) : null
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
ChannelViewListItem.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  view: mosaicSingleView,
  currentMeta: metadataType,
  selectView: PropTypes.func,
  isSelectable: PropTypes.bool,
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
    case MediaType.VIDEO:
      return <ChannelVideo mediaURL={mediaURL} />
    case MediaType.IMAGE:
    default:
      return <ChannelImage mediaURL={mediaURL} />
  }
}
ChannelMedia.propTypes = {
  locationName: PropTypes.string,
  camera: cameraType,
  event: eventType,
  mediaType: PropTypes.shape({
    value: PropTypes.string,
  }),
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
  const vidID = `v_${getStrHashCode(mediaURL)}`
  return (
    <div className="viewVideo">
      <a href={videoSrc}>
        <video
          className="resp"
          id={vidID}
          autoPlay
          loop
          controls
          onLoadedData={() => setIsLoaded(true)}
        >
          <source src={videoSrc} />
        </video>
      </a>
      {isLoaded && (
        <div className="video-extra-controls">
          <button onClick={() => frameStep(vidID, BACK)}>&lt;</button>
          <button onClick={() => frameStep(vidID, FORWARD)}>&gt;</button>
        </div>
      )}
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
  const video = _getById(vidID)
  pauseVideo(video)
  const currentTime = video.currentTime
  const duration = video.duration
  if (timeDelta < 0 && currentTime + timeDelta < 0) {
    video.currentTime = 0
  } else if (
    timeDelta > 0 &&
    currentTime + timeDelta >= duration - FRAMELENGTH
  ) {
    video.currentTime = video.duration
  } else {
    video.currentTime = currentTime + timeDelta
  }
}

window.onkeydown = videoControl

function videoControl(e) {
  const video = document.querySelector(".view-video.selected video")
  if (!video) {
    return
  }
  const key = e.code
  let timeDelta = 0
  switch (key) {
    case "ArrowLeft":
      timeDelta = BACK
      break
    case "ArrowRight":
      timeDelta = FORWARD
      break
  }
  if (timeDelta) {
    frameStep(video.id, timeDelta)
  }
}

function pauseVideo(video) {
  if (!video.paused) {
    video.pause()
  }
}
