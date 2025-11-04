import React from "react"
import { ButtonProps } from "./componentTypes"

export default function Button({
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
