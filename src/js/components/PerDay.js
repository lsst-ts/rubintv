import React, { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { cameraType, eventType } from './componentPropTypes'

function PerDayChannels ({ camera, date, perDay }) {
  const baseUrl = window.APP_DATA.baseUrl
  const locationName = document.documentElement.dataset.locationname
  const channels = camera.channels
  return (
    (perDay && Object.entries(perDay).length > 0) && (
      <nav id="per-day-menu" className="channel-menu" role="navigation">
      <h3>Per Day Channels</h3>
        <ul className="channels flr">
          { Object.entries(perDay).map(([channelName, event]) => {
            const channel = channels[channels.map((chan) => chan.name).indexOf(channelName)]
            const label = channel.label ? channel.label : channel.title
            const filename = event.filename
            return (
              <li className="channel" key={channelName}>
                <a
                  className={`button button-large ${channelName}`}
                  href={`${baseUrl}event_video/${locationName}/${camera.name}/${channelName}/${filename}`}
                  style={
                    { backgroundColor: channel.colour }
                  }
                >
                  <img src={`${baseUrl}static/images/${channelName}.svg`} />
                  {label}
                  <span className="date">{ date }</span>
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    )
  )
}
PerDayChannels.propTypes = {
  /** The current camera.
   */
  camera: cameraType,
  /** perDay is an object with channel names as keys and single events as
   * values.
   */
  perDay: PropTypes.objectOf(eventType),
  /** The chosen date. */
  date: PropTypes.string
}

function NightReportLink ({ camera, date, nightReportLink }) {
  if (nightReportLink === "") {
    return null
  }
  const baseUrl = window.APP_DATA.baseUrl
  const locationName = document.documentElement.dataset.locationname

  let link = `${baseUrl}${locationName}/${camera.name}/night_report/${date}`
  let label = `${camera.night_report_label} for ${date}`
  if (nightReportLink === "current") {
    link = `${baseUrl}${locationName}/${camera.name}/night_report`
    label = camera.night_report_label
  }

  return (
    <div id="night_report_link">
      <h3>Night Report</h3>
      <a
        className="button button-large night-report"
        href={link}>
          <img src={`${baseUrl}static/images/crescent-moon.svg`} />
          {label}
      </a>
    </div>
  )
}
NightReportLink.propTypes = {
  camera: cameraType,
  date: PropTypes.string,
  nightReportLink: PropTypes.string,
}

export default function PerDay ({ camera, initialDate, initialPerDay, initialNRLink }) {
  const [date, setDate] = useState(initialDate)
  const [perDay, setPerDay] = useState(initialPerDay)
  const [nightReportLink, setNightReportLink] = useState(initialNRLink)

  useEffect(() => {
    function handleCameraEvent (event) {
      const { datestamp, data, dataType } = event.detail

      if (datestamp && datestamp !== date) {
        window.APP_DATA.date = datestamp
        setDate(datestamp)
        setPerDay({})
        setNightReportLink("")
      }

      if (dataType === 'perDay' && data != "nightReportExists") {
        setPerDay(data)
      }
      else if (dataType === 'perDay' && data == "nightReportExists") {
        setNightReportLink("current")
      }
    }
    window.addEventListener('camera', handleCameraEvent)

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('camera', handleCameraEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  return (
    <>
      <PerDayChannels camera={camera} date={date} perDay={perDay} />
      <NightReportLink
      camera={camera}
      date={date}
      nightReportLink={nightReportLink} />
    </>
  )
}
PerDay.propTypes = {
  camera: cameraType,
  initialPerDay: PropTypes.objectOf(eventType),
  initialDate: PropTypes.string,
  /** True if a night report event exists for this date. */
  nightReportLink: PropTypes.string,
}
