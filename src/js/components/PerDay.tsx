import React, { useState, useEffect } from "react"
import { homeUrl } from "../config"
import { getImageAssetUrl } from "../modules/utils"
import Button from "./Button"
import {
  PerDayChannelsProps,
  NightReportLinkProps,
  PerDayProps,
} from "../components/componentTypes"

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
  if (!perDay || Object.keys(perDay).length === 0 || nightReportLink === "") {
    return null
  }
  return (
    <div id="per-day" className="columns">
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
    </div>
  )
}
