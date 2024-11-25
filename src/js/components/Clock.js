import React, { useState, useEffect } from "react"

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
  const [time, setTime] = useState(new Date())
  const [metadata, setMetadata] = useState(propsMeta)

  useEffect(() => {
    const timerId = setInterval(() => {
      setTime(Date.now())
    }, 1000)

    function handleWSStateChangeEvent(event) {
      const { online } = event.detail
      setIsOnline(online)
    }
    window.addEventListener("ws_status_change", handleWSStateChangeEvent)

    function handleChannelMetadata(event) {
      const { data, dataType } = event.detail
      if (dataType === "metadata") {
        setMetadata(data)
      }
    }
    window.addEventListener("channel", handleChannelMetadata)

    return () => {
      clearInterval(timerId)
      window.removeEventListener("ws_status_change")
      window.removeEventListener("channel")
    }
  }, [])

  let row = {}
  if (metadata) {
    const lastSeq = Object.entries(metadata)
      .map(([seq]) => parseInt(seq))
      .pop()
    row = metadata[lastSeq]
  }
  const toSum = ["Date begin", "Exposure time"]
  let error, timeElapsed
  if (
    !toSum.reduce((acc, col) => Object.keys(row).includes(col) && acc, true)
  ) {
    console.log(`Can't make Time Since Last Image with:`, row)
    error = "Can't ascertain..."
  } else {
    const startTime = Date.parse(row["Date begin"])
    const exposureTime = row["Exposure time"] * 1000
    const endTime = startTime + exposureTime
    timeElapsed = time - endTime
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

const toTimeString = (timestamp) => {
  const _24HOURS = 8.64e7 // 24*60*60*1000
  const endPos = ~(4 * !!timestamp) // to trim "Z" or ".sssZ"
  let timeString = new Date(timestamp).toISOString().slice(11, endPos)

  if (timestamp >= _24HOURS) {
    // to extract ["hh", "mm:ss[.mss]"]
    var parts = timeString.split(/:(?=\d{2}:)/)
    parts[0] -= -24 * Math.floor(timestamp / _24HOURS)
    timeString = parts.join(":")
  }

  return timeString
}
