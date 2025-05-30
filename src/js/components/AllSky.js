import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import RubinCalendar from "./RubinCalendar"
import { getMediaProxyUrl, getHistoricalData } from "../modules/utils"
import { calendarType, cameraType, eventType } from "./componentPropTypes"

export default function AllSky({
  isHistorical,
  locationName,
  camera,
  calendar,
}) {
  const [date, setDate] = useState(window.APP_DATA.date)
  const [perDayData, setPerDayData] = useState({ stills: {}, movies: {} })
  useEffect(() => {
    window.addEventListener("camera", (message) => {
      const { datestamp, data, dataType } = message.detail
      if (dataType !== "perDay") {
        return
      }
      if (datestamp !== date) {
        document.getElementById("header-date").textContent = datestamp
        setDate(datestamp)
      }
      setPerDayData((prevData) => {
        console.log("Updating perDayData", prevData, data)
        return { ...prevData, ...data }
      })
    })
    return () => {
      window.removeEventListener("camera", (message) => {})
    }
  }, [])

  useEffect(() => {
    async function fetchHistoricalData() {
      if (isHistorical) {
        const json = await getHistoricalData(locationName, camera.name, date)
        if (!json) {
          console.error(
            "No historical data found for",
            locationName,
            camera.name,
            date
          )
          return
        }
        const { perDay } = JSON.parse(json)
        if (!perDay || Object.keys(perDay).length === 0) {
          console.error("No perDay data found for", date)
          return
        }
        setPerDayData(perDay)
      }
    }
    fetchHistoricalData()
  }, [])

  return (
    <>
      <h3 className="date">
        <span>{date}</span>
      </h3>
      <div className="columns">
        {isHistorical ? (
          <section className="calendar half-width">
            <RubinCalendar
              selectedDate={date}
              initialCalendarData={calendar}
              camera={camera}
              locationName={locationName}
            />
          </section>
        ) : (
          <AllSkyStill still={perDayData.stills} locationName={locationName} />
        )}
        <AllSkyMovie movie={perDayData.movies} locationName={locationName} />
      </div>
    </>
  )
}
AllSky.propTypes = {
  isHistorical: PropTypes.bool,
  locationName: PropTypes.string.isRequired,
  camera: cameraType.isRequired,
  calendar: calendarType,
}

function AllSkyStill({ still, locationName }) {
  if (!still || Object.keys(still).length === 0) {
    return null
  }
  const imgUrl = getMediaProxyUrl(
    "image",
    locationName,
    still.camera_name,
    "stills",
    still.filename
  )
  return (
    <section className="allsky-current-image">
      <div className="current-still">
        <div className="subheader">
          <h3>Image {still.seq_num}</h3>
        </div>
        <a target="_blank" href={imgUrl}>
          <img className="resp" src={imgUrl} />
        </a>
        <div className="desc">{still.filename}</div>
      </div>
    </section>
  )
}
AllSkyStill.propTypes = {
  still: eventType,
  locationName: PropTypes.string.isRequired,
}

function AllSkyMovie({ movie, locationName }) {
  if (!movie || Object.keys(movie).length === 0) {
    return null
  }
  const videoUrl = getMediaProxyUrl(
    "video",
    locationName,
    movie.camera_name,
    "movies",
    movie.filename
  )
  return (
    <section className="allsky-current-movie">
      <div className="current-movie">
        <div className="subheader">
          <h3>
            &nbsp;Images 1 &#8594;&nbsp;
            <span className="movie-number">{movie.seq_num}</span>
          </h3>
        </div>
        <video width="100%" controls autoPlay loop>
          <source src={videoUrl} type="video/mp4" />
        </video>
        <div className="desc">{movie.filename}</div>
      </div>
    </section>
  )
}
AllSkyMovie.propTypes = {
  movie: eventType,
  locationName: PropTypes.string.isRequired,
}
