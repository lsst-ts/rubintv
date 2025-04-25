import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import { TimeSinceLastImageClock } from "./Clock"
import PrevNext from "./PrevNext"
import { getBaseFromEventUrl, getMediaType } from "../modules/utils"
import { eventType, cameraType, metadataType } from "./componentPropTypes"

// MediaDisplay component to handle the image/video display
export default function MediaDisplay({
  initialEvent,
  imgUrl,
  videoUrl,
  camera,
  metadata,
  eventUrl,
  prevNext,
  isCurrent = false,
}) {
  const [mediaEvent, setMediaEvent] = useState(() =>
    unifyMediaEvent(initialEvent, imgUrl, videoUrl)
  )
  useEffect(() => {
    const handleChannelEvent = (message) => {
      const { data: event, dataType } = message.detail
      if (dataType !== "event" || !event) {
        return
      }
      setMediaEvent({
        ...unifyMediaEvent(event, imgUrl, videoUrl),
      })
    }

    window.addEventListener("channel", handleChannelEvent)
    return () => {
      window.removeEventListener("channel", handleChannelEvent)
    }
  }, [imgUrl, videoUrl])
  return (
    <>
      <div className="event-info">
        <h2>
          <span className="media-date">{mediaEvent.day_obs}</span>
          <span className="media-seqnum">{mediaEvent.seq_num}</span>
        </h2>
        {isCurrent ? (
          <PrevNext prevNext={prevNext} eventUrl={eventUrl} />
        ) : (
          <TimeSinceLastImageClock metadata={metadata} camera={camera} />
        )}
      </div>
      <a
        className="event-link"
        href={mediaEvent.src}
        target="_blank"
        rel="noopener noreferrer"
      >
        {mediaEvent.mediaType === "video" ? (
          <video
            className="resp"
            id="eventVideo"
            src={mediaEvent.src}
            controls
          />
        ) : (
          <img className="resp" id="eventImage" src={mediaEvent.src} />
        )}
        <p className="desc">{mediaEvent.filename}</p>
      </a>
    </>
  )
}
MediaDisplay.propTypes = {
  initialEvent: eventType,
  imgUrl: PropTypes.string.isRequired,
  videoUrl: PropTypes.string.isRequired,
  camera: cameraType,
  metadata: metadataType,
  eventUrl: PropTypes.string,
  prevNext: PropTypes.shape({
    prev: eventType,
    next: eventType,
  }),
  isCurrent: PropTypes.bool,
}

/**
 *
 * @param {Object} mEvent
 * @param {string} imgUrl
 * @param {string} videoUrl
 * @returns {Object}
 * @description This function takes a media event and returns a unified media
 * event object with the correct media type and source URL.
 * It determines the media type based on the file extension and constructs
 * the source URL using the filename and base URL. The media type can be
 * either "image" or "video".
 */
function unifyMediaEvent(mEvent, imgUrl, videoUrl) {
  const { filename, ext } = mEvent
  const mediaType = getMediaType(ext)
  const url = mediaType === "video" ? videoUrl : imgUrl
  const baseImgUrl = getBaseFromEventUrl(url)
  const src = new URL(filename, baseImgUrl).toString()
  return {
    ...mEvent,
    mediaType,
    src,
  }
}
