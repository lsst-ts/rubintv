import React, { useState, useEffect } from "react"
import { TimeSinceLastImageClock } from "./Clock"
import PrevNext from "./PrevNext"
import {
  getBaseFromEventUrl,
  getMediaType,
  getMediaProxyUrl,
  getCameraPageForDateUrl,
  getDocumentLocation,
} from "../modules/utils"
import {
  ExposureEvent,
  Metadata,
  RubinTVContextType,
  MediaDisplayProps,
  BundledMediaEvent,
  OtherChannelLinksProps,
} from "./componentTypes"
import { RubinTVTableContext } from "./contexts/contexts"

type EL = EventListener

// MediaDisplay component to handle the image/video display
export default function MediaDisplay({
  locationName,
  camera,
  initEvent,
  prevNext,
  allChannelNames,
  isCurrent = false,
}: MediaDisplayProps) {
  const [mediaEvent, setMediaEvent] = useState<BundledMediaEvent | null>(() => {
    if (!initEvent) {
      return null
    }
    return bundleMediaEventData(initEvent, locationName)
  })

  useEffect(() => {
    const handleChannelEvent = (message: CustomEvent) => {
      const { data, dataType } = message.detail
      if (dataType !== "event" || !data) {
        return
      }
      const event = data as ExposureEvent
      const bundledEvent = bundleMediaEventData(event, locationName)
      setMediaEvent(bundledEvent)
    }

    window.addEventListener("channel", handleChannelEvent as EL)
    return () => {
      window.removeEventListener("channel", handleChannelEvent as EL)
    }
  }, [])

  if (!mediaEvent) {
    return null
  }

  const dateUrl = getCameraPageForDateUrl(
    locationName,
    camera.name,
    mediaEvent.day_obs
  )
  return (
    <RubinTVTableContext.Provider
      value={
        {
          camera,
          siteLocation: "",
          locationName: locationName,
          dayObs: mediaEvent.day_obs,
        } as RubinTVContextType
      }
    >
      <div className="event-info">
        <h2>
          <a href={dateUrl} className="media-date">
            {mediaEvent.day_obs}
          </a>
          <span className="media-seqnum">{mediaEvent.seq_num}</span>
        </h2>
        <PrevNext initialPrevNext={prevNext} />
        {isCurrent && camera.time_since_clock ? (
          <TimeSinceLastImageClock
            metadata={{} as Metadata}
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
    </RubinTVTableContext.Provider>
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
  locationName: string
): BundledMediaEvent {
  const { filename, ext } = mEvent
  const mediaType = getMediaType(ext)
  const url = getMediaProxyUrl(
    mediaType,
    locationName,
    mEvent.camera_name,
    mEvent.channel_name,
    filename
  )
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

  const currentUrl = getDocumentLocation()
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
