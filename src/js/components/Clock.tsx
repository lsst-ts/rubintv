import React, { useState, useEffect } from "react"
import { toTimeString } from "../modules/utils"
import { Metadata, Camera } from "./componentTypes"

interface CameraWithTimeSinceClock extends Camera {
  time_since_clock: {
    label: string
  }
}

export default function Clock() {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timerId = setInterval(() => {
      setTime(new Date())
    }, 1000)

    return () => {
      clearInterval(timerId)
    }
  }, [])

  const hoursMins = getHoursAndMins(time)
  const secs = padZero(time.getUTCSeconds())
  return (
    <div className="clock">
      <div>
        <span className="hours-mins">{hoursMins}</span>
        <span className="secs">{secs}</span>
      </div>
    </div>
  )
}

function getHoursAndMins(time: Date): string {
  const h = padZero(time.getUTCHours())
  const m = padZero(time.getUTCMinutes())
  return h + ":" + m
}

function padZero(num: number): string {
  return (num + 100).toString().slice(-2)
}

export function TimeSinceLastImageClock({
  metadata: propsMeta,
  camera,
}: {
  metadata: Metadata
  camera: CameraWithTimeSinceClock
}) {
  const [isOnline, setIsOnline] = useState(true)
  const [time, setTime] = useState(Date.now())
  const [metadata, setMetadata] = useState(propsMeta)

  // TAI and UTF are out by ~37s
  const TAIDIFF = 37 * 1000

  useEffect(() => {
    type EV = EventListener
    const timerId = setInterval(() => {
      setTime(Date.now())
    }, 1000)

    function handleWSStateChange(event: CustomEvent) {
      const { online } = event.detail
      setIsOnline(online)
    }
    window.addEventListener("ws_status_change", handleWSStateChange as EV)

    function handleMetadataChange(event: CustomEvent) {
      const { data, dataType } = event.detail
      if (dataType === "metadata" && Object.entries(data).length > 0) {
        setMetadata(data)
      }
    }
    window.addEventListener("camera", handleMetadataChange as EV)

    // Listen for the latest metadata change event
    // This is just one seq_num, not the whole metadata
    // that is sent via a "channel" ws event
    function handleLatestMetadataChange(event: CustomEvent) {
      const { data, dataType } = event.detail
      console.debug(
        "TimeSinceLastImageClock: handleLatestMetadataChange",
        dataType,
        data
      )
      if (dataType === "latestMetadata") {
        setMetadata(data)
      }
    }
    window.addEventListener("channel", handleLatestMetadataChange as EV)

    return () => {
      clearInterval(timerId)
      window.removeEventListener("ws_status_change", handleWSStateChange as EV)
      window.removeEventListener("camera", handleMetadataChange as EV)
      window.removeEventListener("channel", handleLatestMetadataChange as EV)
    }
  }, [])

  const lastSeq = metadata
    ? Object.keys(metadata)
        .map(Number)
        .sort((a, b) => a - b)
        .pop()
    : undefined

  const row = lastSeq !== undefined ? metadata[lastSeq] : undefined

  if (!row) {
    return null
  }

  const className = ["clock time-since-clock", isOnline ? "" : "offline"].join(
    " "
  )
  const requiredFields = ["Date begin", "Exposure time"] as const
  const missingField = requiredFields.find((col) => !(col in row))

  if (missingField) {
    return (
      <div className={className}>
        <div>
          {isOnline && (
            <p>
              <span className="label">{camera.time_since_clock.label}</span>
              <span>Can&#39;t ascertain...</span>
            </p>
          )}
          {!isOnline && <p>Lost comms with app</p>}
        </div>
      </div>
    )
  }

  let UTCDateString = row["Date begin"] as string
  if (!UTCDateString.endsWith("Z")) {
    UTCDateString += "Z"
  }
  const startTime = Date.parse(UTCDateString)
  const exposureTime = row["Exposure time"] as number
  const endTime = startTime + (exposureTime ? exposureTime * 1000 : 0)
  const timeElapsed = time - endTime + TAIDIFF

  return (
    <div className={className}>
      <div>
        {isOnline && (
          <p>
            <span className="label">{camera.time_since_clock.label}</span>
            {timeElapsed && (
              <span className="timeElapsed">{toTimeString(timeElapsed)}</span>
            )}
          </p>
        )}
        {!isOnline && <p>Lost comms with app</p>}
      </div>
    </div>
  )
}
