import React from "react"
import { homeUrl } from "../config"
import Button from "./Button"
import { CurrentChannelsProps } from "../components/componentTypes"

export default function CurrentChannels({
  locationName,
  camera,
}: CurrentChannelsProps) {
  return (
    <section id="current-channels">
      <nav
        id="current-channels-menu"
        className="channel-menu"
        role="navigation"
      >
        <h3>Current Image Channels</h3>
        <ul className="channels flr">
          {camera.channels
            .filter((channel) => !channel.per_day)
            .map((channel) => {
              const label = channel.label ? channel.label : channel.title
              const url = `${homeUrl}${locationName}/${camera.name}/current/${channel.name}`
              return (
                <li className="channel service" key={channel.name}>
                  <Button
                    clsName={channel.name}
                    url={url}
                    bckCol={channel.colour}
                    textColour={channel.text_colour}
                    label={label}
                  />
                </li>
              )
            })}
        </ul>
      </nav>
    </section>
  )
}
