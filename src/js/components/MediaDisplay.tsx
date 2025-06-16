import React, { useState, useEffect } from "react"
import { TimeSinceLastImageClock } from "./Clock"
import PrevNext from "./PrevNext"
import { getBaseFromEventUrl, getMediaType } from "../modules/utils"
import {
  ExposureEvent,
  Camera,
  Metadata,
  PrevNextType,
  TableContext,
  TableContextType,
} from "./componentTypes"

interface MediaEventProps {
  locationName: string
  initialEvent: ExposureEvent
  imgUrl: string
  videoUrl: string
  camera: Camera
  dateUrl: string
  metadata: Metadata
  eventUrl: string
  prevNext: PrevNextType
  allChannelNames: string[]
  isCurrent: boolean
}

interface BundledMediaEvent extends ExposureEvent {
  mediaType: "image" | "video"
  src: string
}

interface OtherChannelLinksProps {
  allChannelNames: string[]
  thisChannel: string
  camera: Camera
}

// MediaDisplay component to handle the image/video display
export default function MediaDisplay({
  locationName,
  initialEvent,
  imgUrl,
  videoUrl,
  camera,
  dateUrl,
  metadata,
  eventUrl,
  prevNext,
  allChannelNames,
  isCurrent = false,
}: MediaEventProps) {
  const [mediaEvent, setMediaEvent] = useState(() =>
    bundleMediaEventData(initialEvent, imgUrl, videoUrl)
  )

  useEffect(() => {
    type EL = EventListener
    const handleChannelEvent = (message: CustomEvent) => {
      const { data, dataType } = message.detail
      if (dataType !== "event" || !data) {
        return
      }
      const event = data as ExposureEvent
      setMediaEvent({
        ...bundleMediaEventData(event, imgUrl, videoUrl),
      })
    }

    window.addEventListener("channel", handleChannelEvent as EL)
    return () => {
      window.removeEventListener("channel", handleChannelEvent as EL)
    }
  }, [imgUrl, videoUrl])

  return (
    <TableContext.Provider
      value={
        {
          camera,
          siteLocation: "",
          locationName: locationName,
          dayObs: mediaEvent.day_obs,
        } as TableContextType
      }
    >
      <div className="event-info">
        <h2>
          <a href={dateUrl} className="media-date">
            {mediaEvent.day_obs}
          </a>
          <span className="media-seqnum">{mediaEvent.seq_num}</span>
        </h2>
        <PrevNext initialPrevNext={prevNext} eventUrl={eventUrl} />
        {isCurrent && camera.time_since_clock ? (
          <TimeSinceLastImageClock
            metadata={metadata}
            camera={{
              ...camera,
              time_since_clock: camera.time_since_clock ?? { label: "" },
            }}
          />
        ) : null}
      </div>
      <div className="event-nav">
        <OtherChannelLinks
          allChannelNames={allChannelNames}
          thisChannel={mediaEvent.channel_name}
          camera={camera}
        />
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
    </TableContext.Provider>
  )
}

/**
 * This function takes a media event and returns a unified media
 * event object with the correct media type and source URL.
 * It determines the media type based on the file extension and constructs
 * the source URL using the filename and base URL. The media type can be
 * either "image" or "video".
 */
function bundleMediaEventData(
  mEvent: ExposureEvent,
  imgUrl: string,
  videoUrl: string
): BundledMediaEvent {
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

const OtherChannelLinks = ({
  allChannelNames,
  thisChannel,
  camera,
}: OtherChannelLinksProps) => {
  const [channelNames, setChannelNames] = useState(allChannelNames)

  useEffect(() => {
    type EL = EventListener
    function handleChannelNamesChange(event: CustomEvent) {
      const { data: newChannelNames } = event.detail
      if (!newChannelNames || !Array.isArray(newChannelNames)) {
        return
      }
      if (newChannelNames.length > 0) {
        setChannelNames(newChannelNames)
      }
    }
    window.addEventListener("channel", handleChannelNamesChange as EL)
    return () => {
      window.removeEventListener("channel", handleChannelNamesChange as EL)
    }
  }, [channelNames])

  const currentUrl = document.location.toString()
  const buildUrl = (channelName: string) => {
    if (currentUrl.endsWith(`${thisChannel}/current`)) {
      return currentUrl.replace(thisChannel, channelName)
    } else {
      return currentUrl.replace(
        `channel_name=${thisChannel}`,
        `channel_name=${channelName}`
      )
    }
  }
  return (
    <div className="other-channels">
      {camera.channels.map((channel) => {
        if (!channelNames.includes(channel.name)) {
          return null
        }
        const chanStyle = {
          backgroundColor: channel.colour,
          color: channel.text_colour,
        }
        // Construct the URL for each channel
        const channelUrl = buildUrl(channel.name)
        return (
          <a
            key={channel.name}
            href={channelUrl}
            style={chanStyle}
            className="button"
          >
            {channel.title}
          </a>
        )
      })}
    </div>
  )
}
