import React, { useState, useEffect } from 'react'
import propTypes from 'prop-types'

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
            const filename = event.filename + '.' + event.ext
            return (
              <li className="channel" key={channelName}>
                <a className={`button button-large ${channelName}`}
                  href={`${baseUrl}event_video/${locationName}/${camera.name}/${channelName}/${filename}`}
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
  camera: propTypes.object,
  perDay: propTypes.object,
  date: propTypes.string
}

function NightReportLink ({ camera, date, nightReportExists }) {
  if (!nightReportExists) {
    return null
  }
  const isHistorical = window.APP_DATA.ishistorical
  const baseUrl = window.APP_DATA.baseUrl
  const locationName = document.documentElement.dataset.locationname
  let label
  let link
  if (!isHistorical) {
    link = `${baseUrl}${locationName}/${camera.name}/night_report`
    label = camera.night_report_label
  } else {
    link = `${baseUrl}${locationName}/${camera.name}/night_report/${date}`
    label = `${camera.night_report_label} for ${date}`
  }
  return (
    <div id="night_report_link">
      <h3>{label}</h3>
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
  camera: propTypes.object,
  date: propTypes.string,
  nightReportExists: propTypes.bool
}

export default function PerDay ({ camera, initialDate, initialPerDay, nightReportExists }) {
  const [date, setDate] = useState(initialDate)
  const [perDay, setPerDay] = useState(initialPerDay)

  useEffect(() => {
    function handleCameraEvent (event) {
      console.debug('TableApp event:', event)
      const { datestamp, data, dataType } = event.detail

      if (datestamp && datestamp !== date) {
        setDate(datestamp)
      }

      if (dataType === 'per_day') {
        setPerDay(data)
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
      <NightReportLink camera={camera} date={date} nightReportExists={nightReportExists} />
    </>
  )
}
PerDay.propTypes = {
  camera: propTypes.object,
  initialPerDay: propTypes.object,
  initialDate: propTypes.string,
  nightReportExists: propTypes.bool,
  hasCalendar: propTypes.bool
}
