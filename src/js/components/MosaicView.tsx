import React, { useState, useEffect } from "react"
import { _getById, getStrHashCode } from "../modules/utils"
import { homeUrl } from "../config"
import {
  Camera,
  MosiacSingleView,
  MediaType,
  ExposureEvent,
} from "./componentTypes"

interface CameraWithMosaicViewMeta extends Camera {
  mosaic_view_meta: MosiacSingleView[]
}

const FRAMELENGTH = 0.1
const BACK = -FRAMELENGTH
const FORWARD = FRAMELENGTH

const commonColumns = ["seqNum"]

export default function MosaicView({
  locationName,
  camera,
}: {
  locationName: string
  camera: CameraWithMosaicViewMeta
}) {
  const [currentMeta, setCurrentMeta] = useState({})
  const [views, setViews] = useState(initialViews)

  function initialViews() {
    let videoCount = 0
    const views = camera.mosaic_view_meta.map((view) => {
      const isVideo = view.mediaType === "video"
      videoCount += isVideo ? 1 : 0
      return {
        ...view,
        mediaType: view.mediaType,
        latestEvent: undefined,
        // only apply 'selected == true' to first video
        selected: isVideo && videoCount == 1 ? true : false,
      }
    })
    return views
  }

  function hasMultipleVideos() {
    // Is there more than one video?
    const vids = camera.mosaic_view_meta.filter(
      ({ mediaType }) => mediaType === "video"
    )
    return vids.length > 1 ? true : false
  }

  function selectView(thisView: MosiacSingleView) {
    setViews((prevViews) =>
      prevViews.map((view) =>
        view.channel === thisView.channel
          ? { ...view, selected: true }
          : { ...view, selected: false }
      )
    )
  }

  useEffect(() => {
    type EV = EventListener
    window.addEventListener("camera", handleMetadataChange as EV)
    window.addEventListener("channel", handleChannelEvent as EV)

    function handleMetadataChange(event: CustomEvent) {
      const { data, dataType } = event.detail
      if (Object.entries(data).length < 1 || dataType !== "metadata") {
        return
      }
      setCurrentMeta(data)
    }

    /**
     * Handle the channel event to update the views with the latest event data.
     * This is triggered when a new event occurs on a channel.
     */
    function handleChannelEvent(event: CustomEvent) {
      const { data } = event.detail

      if (!data || Object.keys(data).length < 1) {
        console.warn("No data received in channel event")
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
      window.removeEventListener("camera", handleMetadataChange as EV)
      window.removeEventListener("channel", handleChannelEvent as EV)
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

function ChannelViewListItem({
  locationName,
  camera,
  view,
  currentMeta,
  selectView,
  isSelectable,
}: {
  locationName: string
  camera: CameraWithMosaicViewMeta
  view: MosiacSingleView
  currentMeta: Record<string, Record<string, string>>
  selectView: (view: MosiacSingleView) => void
  isSelectable: boolean
}) {
  const channel = camera.channels.find(({ name }) => name === view.channel)
  if (!channel) {
    return <h3>Channel {view.channel} not found</h3>
  }
  const { selected, mediaType } = view
  const dayObs = view.latestEvent?.day_obs
  const clsName = ["view", `view-${mediaType}`, selected ? "selected" : null]
    .join(" ")
    .trimEnd()
  const clickHandler = isSelectable ? () => selectView(view) : undefined
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

function ChannelMedia({
  locationName,
  camera,
  event,
  mediaType,
}: {
  locationName: string
  camera: CameraWithMosaicViewMeta
  event: ExposureEvent | undefined
  mediaType: MediaType
}) {
  if (!event || !event.filename) return <ChannelMediaPlaceholder />
  const mediaURL = buildMediaURI(
    locationName,
    camera.name,
    event.channel_name,
    event.filename
  )
  switch (mediaType) {
    case "video":
      return <ChannelVideo mediaURL={mediaURL} />
    case "image":
    default:
      return <ChannelImage mediaURL={mediaURL} />
  }
}

function ChannelImage({ mediaURL }: { mediaURL: string }) {
  const imgSrc = new URL(`event_image/${mediaURL}`, homeUrl).toString()
  return (
    <div className="viewImage">
      <a href={imgSrc}>
        <img className="resp" src={imgSrc} />
      </a>
    </div>
  )
}

function ChannelVideo({ mediaURL }: { mediaURL: string }) {
  const [isLoaded, setIsLoaded] = useState(false)
  const videoSrc = new URL(`event_video/${mediaURL}`, homeUrl).toString()
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

function ChannelMediaPlaceholder() {
  return (
    <div className="viewImage placeholder">
      <h4 className="image-placeholder">Nothing today yet</h4>
    </div>
  )
}

function ChannelMetadata({
  view,
  metadata,
}: {
  view: MosiacSingleView
  metadata: Record<string, Record<string, string>>
}) {
  const { channel, metaColumns: viewColumns, latestEvent } = view
  if (
    viewColumns.length == 0 ||
    !latestEvent ||
    latestEvent.seq_num === undefined
  ) {
    return
  }
  const columns = [...commonColumns, ...viewColumns]
  const metadatum = metadata[latestEvent.seq_num] || {}
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

const buildMediaURI = (
  locationName: string,
  cameraName: string,
  channelName: string,
  filename: string
) => `${locationName}/${cameraName}/${channelName}/${filename}`

function frameStep(vidID: string, timeDelta: number) {
  const video = _getById(vidID) as HTMLVideoElement
  if (!video) {
    console.warn(`Video with ID ${vidID} not found`)
    return
  }
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

function videoControl(e: KeyboardEvent) {
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

function pauseVideo(video: HTMLVideoElement) {
  if (!video.paused) {
    video.pause()
  }
}
