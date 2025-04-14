import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import { cameraType, eventType } from "./componentPropTypes"

function Button({
  clsName,
  url,
  bckCol,
  iconUrl,
  logoURL,
  label,
  date,
  textColour,
  textShadow,
}) {
  const style = {
    backgroundColor: bckCol,
    color: textColour,
    backgroundImage: logoURL ? `url(${logoURL})` : "none",
    backgroundSize: "contain",
  }
  clsName = logoURL ? clsName + " button-logo" : clsName
  clsName = textShadow ? clsName + " t-shadow" : clsName

  return (
    <a className={`button button-large ${clsName}`} href={url} style={style}>
      {iconUrl && <img src={iconUrl} />}
      {label}
      {date && <span className="date">{date}</span>}
    </a>
  )
}
Button.propTypes = {
  clsName: PropTypes.string,
  url: PropTypes.string,
  bckCol: PropTypes.string,
  iconUrl: PropTypes.object,
  logoURL: PropTypes.object,
  label: PropTypes.string,
  date: PropTypes.string,
  textColour: PropTypes.string,
  textShadow: PropTypes.string,
}

function PerDayChannels({ camera, date, perDay }) {
  const {
    homeUrl,
    imagesURL: imageRoot,
    isHistorical,
    locationName,
  } = window.APP_DATA
  const channels = camera.channels

  const getImageURL = (path) => {
    const [base, queriesMaybe] = imageRoot.split("?")
    const queries = queriesMaybe ? "?" + queriesMaybe : ""
    return new URL(path + queries, base + "/")
  }

  return (
    perDay &&
    Object.entries(perDay).length > 0 && (
      <nav id="per-day-menu" className="channel-menu" role="navigation">
        <h3>Per Day Channels</h3>
        <ul className="channels flr">
          {perDay &&
            Object.entries(perDay).map(([channelName, event]) => {
              const channel =
                channels[channels.map((chan) => chan.name).indexOf(channelName)]
              const label = channel.label ? channel.label : channel.title
              const filename = event.filename
              const url = `${homeUrl}event_video/${locationName}/${camera.name}/${channelName}/${filename}`
              const icon = channel.icon === "" ? channelName : channel.icon
              const iconUrl = getImageURL(`${icon}.svg`)
              return (
                <li className="channel" key={channelName}>
                  <Button
                    clsName={channelName}
                    url={url}
                    bckCol={channel.colour}
                    iconUrl={iconUrl}
                    label={label}
                    date={date}
                  />
                </li>
              )
            })}
          {!isHistorical &&
            camera.extra_buttons.map(
              ({ name, title, linkURL, logo, text_colour, text_shadow }) => {
                const logoURL = getImageURL(`logos/${logo}`)
                return (
                  <li className="channel" key={name}>
                    <Button
                      clsName={name}
                      url={new URL(linkURL, location.href + "/")}
                      logoURL={logoURL}
                      label={title}
                      textColour={text_colour}
                      textShadow={text_shadow}
                    />
                  </li>
                )
              }
            )}
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
  date: PropTypes.string,
}

function NightReportLink({ camera, date, nightReportLink }) {
  if (nightReportLink === "") {
    return null
  }
  const { homeUrl, locationName } = window.APP_DATA

  let link = `${homeUrl}${locationName}/${camera.name}/night_report/${date}`
  let label = `${camera.night_report_label} for ${date}`
  if (nightReportLink === "current") {
    link = `${homeUrl}${locationName}/${camera.name}/night_report`
    label = camera.night_report_label
  }

  return (
    <div id="night_report_link">
      <h3>Night&#39;s Evolution</h3>
      <a className="button button-large night-report" href={link}>
        <img src={`${homeUrl}static/images/crescent-moon.svg`} />
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

export default function PerDay({
  camera,
  initialDate,
  initialPerDay,
  initialNRLink,
}) {
  const [date, setDate] = useState(initialDate)
  const [perDay, setPerDay] = useState(initialPerDay)
  const [nightReportLink, setNightReportLink] = useState(initialNRLink)

  useEffect(() => {
    function handleCameraEvent(event) {
      const { datestamp, data, dataType } = event.detail
      if (dataType !== "perDay") {
        return
      }

      if (datestamp && datestamp !== date) {
        window.APP_DATA.date = datestamp
        setDate(datestamp)
        setPerDay({})
        setNightReportLink("")
      }

      if (!data.nightReportLink) {
        setPerDay(data)
      } else {
        setNightReportLink("current")
      }
    }
    window.addEventListener("camera", handleCameraEvent)

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("camera", handleCameraEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  return (
    <>
      <PerDayChannels camera={camera} date={date} perDay={perDay} />
      <NightReportLink
        camera={camera}
        date={date}
        nightReportLink={nightReportLink}
      />
    </>
  )
}
PerDay.propTypes = {
  camera: cameraType,
  initialPerDay: PropTypes.objectOf(eventType),
  initialDate: PropTypes.string,
  /** True if a night report event exists for this date. */
  initialNRLink: PropTypes.string,
}
