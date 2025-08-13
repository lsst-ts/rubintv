import React, { useState, useEffect } from "react"
import { homeUrl } from "../config"
import { getImageAssetUrl } from "../modules/utils"

interface Channel {
  name: string
  label?: string
  title: string
  icon: string
  colour: string
}

interface ExtraButton {
  name: string
  title: string
  linkURL: string
  logo: string
  text_colour?: string
  text_shadow?: boolean
}

interface Camera {
  name: string
  channels: Channel[]
  extra_buttons?: ExtraButton[]
  night_report_label?: string
}

interface Event {
  filename: string
  // Add other event properties as needed
}

interface ButtonProps {
  clsName: string
  url: string
  bckCol?: string
  iconUrl?: string
  logoURL?: string
  label: string
  date?: string
  textColour?: string
  textShadow?: boolean
}

interface PerDayChannelsProps {
  locationName: string
  camera: Camera
  date: string
  perDay: Record<string, Event>
  isHistorical: boolean
}

interface NightReportLinkProps {
  locationName: string
  camera: Camera
  date: string
  nightReportLink: string
}

interface PerDayProps {
  locationName: string
  camera: Camera
  initialDate: string
  initialNRLink: string
  isHistorical: boolean
}

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
}: ButtonProps) {
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

function PerDayChannels({
  locationName,
  camera,
  date,
  perDay,
  isHistorical,
}: PerDayChannelsProps) {
  const channels = camera.channels
  if (!channels || channels.length === 0) {
    console.warn(
      `Camera ${camera.name} has no channels configured, cannot render Per Day Channels`
    )
    return null
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
              if (!channel) {
                console.warn(
                  `Channel ${channelName} not found in camera configuration`
                )
                return null
              }
              const label = channel.label ? channel.label : channel.title
              const filename = event.filename
              const url = `${homeUrl}event_video/${locationName}/${camera.name}/${channelName}/${filename}`
              const icon = channel.icon === "" ? channelName : channel.icon
              const iconUrl = getImageAssetUrl(`${icon}.svg`)
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
            camera.extra_buttons?.map(
              ({ name, title, linkURL, logo, text_colour, text_shadow }) => {
                const logoURL = getImageAssetUrl(`logos/${logo}`)
                return (
                  <li className="channel" key={name}>
                    <Button
                      clsName={name}
                      url={new URL(linkURL, location.href + "/").toString()}
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

function NightReportLink({
  locationName,
  camera,
  date,
  nightReportLink,
}: NightReportLinkProps) {
  if (nightReportLink === "") {
    return null
  }

  let link = `${homeUrl}${locationName}/${camera.name}/night_report/${date}`
  let label = `${camera.night_report_label} for ${date}`
  if (nightReportLink === "current") {
    link = `${homeUrl}${locationName}/${camera.name}/night_report`
    label = camera.night_report_label ? camera.night_report_label : ""
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

export default function PerDay({
  locationName,
  camera,
  initialDate,
  initialNRLink,
  isHistorical,
}: PerDayProps) {
  const [date, setDate] = useState(initialDate)
  const [nightReportLink, setNightReportLink] = useState(initialNRLink)
  const [perDay, setPerDay] = useState({})

  useEffect(() => {
    function handleCameraEvent(event: CustomEvent) {
      const { datestamp, data, dataType } = event.detail
      if (dataType !== "perDay" || !data) {
        return
      }

      if (datestamp && datestamp !== date) {
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
    window.addEventListener("camera", handleCameraEvent as EventListener)

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("camera", handleCameraEvent as EventListener)
    }
  }, [date]) // Only reattach the event listener if the date changes

  return (
    <>
      <PerDayChannels
        locationName={locationName}
        camera={camera}
        date={date}
        perDay={perDay}
        isHistorical={isHistorical}
      />
      <NightReportLink
        locationName={locationName}
        camera={camera}
        date={date}
        nightReportLink={nightReportLink}
      />
    </>
  )
}
