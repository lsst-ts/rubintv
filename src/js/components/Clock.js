/* eslint-disable no-prototype-builtins */
import React, { useState, useEffect } from "react"
import { toTimeString } from "../modules/utils"
import { cameraType, metadataType } from "./componentPropTypes"

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

function getHoursAndMins(time) {
  const h = padZero(time.getUTCHours())
  const m = padZero(time.getUTCMinutes())
  return h + ":" + m
}

function padZero(num) {
  return (num + 100).toString().slice(-2)
}

export function TimeSinceLastImageClock(props) {
  const { metadata: propsMeta, camera } = props

  const [isOnline, setIsOnline] = useState(true)
  const [time, setTime] = useState(Date.now())
  const [metadata, setMetadata] = useState(propsMeta)

  // TAI and UTF are out by ~37s
  const TAIDIFF = 37 * 1000

  useEffect(() => {
    const timerId = setInterval(() => {
      setTime(Date.now())
    }, 1000)

    function handleWSStateChangeEvent(event) {
      const { online } = event.detail
      setIsOnline(online)
    }
    window.addEventListener("ws_status_change", handleWSStateChangeEvent)

    function handleMetadataChange(event) {
      const { data, dataType } = event.detail
      if (dataType === "metadata" && Object.entries(data).length > 0) {
        setMetadata(data)
      }
    }
    window.addEventListener("camera", handleMetadataChange)

    // Listen for the latest metadata change event
    // This is just one seq_num, not the whole metadata
    // that is sent via a "channel" ws event
    function handleLatestMetadataChange(event) {
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
    window.addEventListener("channel", handleLatestMetadataChange)

    return () => {
      clearInterval(timerId)
      window.removeEventListener("ws_status_change", handleWSStateChangeEvent)
      window.removeEventListener("camera", handleMetadataChange)
      window.removeEventListener("channel", handleLatestMetadataChange)
    }
  }, [])

  let row = {}
  if (metadata) {
    const lastSeq = Object.entries(metadata)
      .map(([seq]) => parseInt(seq))
      .pop()
    row = metadata[lastSeq]
  }
  if (!row) {
    return
  }
  const toSum = ["Date begin", "Exposure time"]
  let error, timeElapsed
  if (!toSum.every((col) => row.hasOwnProperty(col))) {
    error = "Can't ascertain..."
  } else {
    let UTCDateString = row["Date begin"]
    if (!UTCDateString.endsWith("Z")) {
      UTCDateString += "Z"
    }
    const startTime = Date.parse(UTCDateString)
    const exposureTime = row["Exposure time"] * 1000
    const endTime = startTime + exposureTime
    timeElapsed = time - endTime + TAIDIFF
  }
  const className = ["clock time-since-clock", isOnline ? "" : "offline"].join(
    " "
  )
  return (
    <div className={className}>
      <div>
        {isOnline && (
          <p>
            <span className="label">{camera.time_since_clock.label}</span>
            {error && <span>{error}</span>}
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
TimeSinceLastImageClock.propTypes = {
  metadata: metadataType,
  camera: cameraType,
}
