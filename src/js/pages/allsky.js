import React from "react"
import { createRoot } from "react-dom/client"
import RubinCalendar from "../components/RubinCalendar"
import { WebsocketClient } from "../modules/ws-service-client.js"
import { _getById } from "../modules/utils.js"
;(function () {
  const { locationName, camera, homeUrl, date, calendar, isHistorical } =
    window.APP_DATA

  if (!isHistorical) {
    console.log("Not historical")
    const ws = new WebsocketClient()
    ws.subscribe("service", "camera", locationName, camera.name)
    window.addEventListener("camera", (message) => {
      const { datestamp, data, dataType } = message.detail
      if (dataType != "perDay") {
        return
      }
      if (datestamp != window.APP_DATA.date) {
        window.APP_DATA.date = datestamp
        _getById("header-date").textContent = datestamp
      }
      const currentImage = document.querySelector(".current-still")
      const currentMovie = document.querySelector(".current-movie")

      Object.entries(data).forEach(([chan, evnt]) => {
        let url
        const filename = evnt.filename
        const seqNum = evnt.seq_num
        const date = evnt.day_obs
        if (chan === "stills") {
          url = `${homeUrl}event_image/${locationName}/${camera.name}/stills/${filename}`
          currentImage.querySelector("img").setAttribute("src", url)
          currentImage.querySelector("a").setAttribute("href", url)
          currentImage.querySelector(
            ".subheader h3"
          ).textContent = `${date} : Image ${seqNum}`
          currentImage.querySelector(".desc").textContent = filename
        }
        if (chan === "movies") {
          url = `${homeUrl}event_video/${locationName}/${camera.name}/movies/${filename}`
          const video = currentMovie.querySelector("video")
          const source = video.querySelector("source")
          source.setAttribute("src", url)
          currentMovie.querySelector(".movie-date").textContent = date
          currentMovie.querySelector(".movie-number").textContent = seqNum
          currentMovie.querySelector(".desc").textContent = filename
          video.load()
        }
      })
    })
  } else {
    const ws = new WebsocketClient()
    ws.subscribe("service", "calendar", locationName, camera.name)

    const calendarRoot = createRoot(_getById("calendar"))
    calendarRoot.render(
      <RubinCalendar
        date={date}
        initialCalendar={calendar}
        camera={camera}
        locationName={locationName}
      />
    )
  }
})()
