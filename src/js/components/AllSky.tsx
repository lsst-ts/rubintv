import React, { useState, useEffect, useRef } from "react"
import RubinCalendar from "./RubinCalendar"
import { getMediaProxyUrl, getHistoricalData } from "../modules/utils"
import { CalendarData, Camera, ExposureEvent } from "./componentTypes"

export default function AllSky({
  initialDate,
  isHistorical,
  locationName,
  camera,
  calendar,
}: {
  initialDate: string
  isHistorical?: boolean
  locationName: string
  camera: Camera
  calendar?: CalendarData
}) {
  const [date, setDate] = useState(initialDate)
  const [perDayData, setPerDayData] = useState({
    stills: {} as ExposureEvent,
    movies: {} as ExposureEvent,
  })

  const dateRef = useRef(initialDate)
  // Update ref when date changes
  useEffect(() => {
    dateRef.current = date
  }, [date])

  useEffect(() => {
    type EL = EventListener
    function handleDataChange(event: CustomEvent) {
      const { datestamp, data, dataType } = event.detail
      if (dataType !== "perDay") {
        return
      }
      if (datestamp !== dateRef.current) {
        const headerDate = document.getElementById("header-date") as HTMLElement
        if (headerDate) {
          headerDate.textContent = datestamp
        }
        setDate(datestamp)
      }
      setPerDayData((prevData) => {
        return { ...prevData, ...data }
      })
    }
    window.addEventListener("camera", handleDataChange as EL)
    return () => {
      window.removeEventListener("camera", handleDataChange as EL)
    }
  }, [])

  // Fetch historical data if required.
  // This will only run once when the component mounts.
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
              initialCalendarData={calendar || {}}
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

function AllSkyStill({
  still,
  locationName,
}: {
  still: ExposureEvent | null
  locationName: string
}) {
  if (!still || Object.keys(still).length === 0) {
    return null
  }

  const imgUrl = getMediaProxyUrl(
    "image",
    locationName,
    still.camera_name,
    "stills",
    still.filename
  ).toString()

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

function AllSkyMovie({
  movie,
  locationName,
}: {
  movie: ExposureEvent | null
  locationName: string
}) {
  if (!movie || Object.keys(movie).length === 0) {
    return null
  }
  const videoUrl = getMediaProxyUrl(
    "video",
    locationName,
    movie.camera_name,
    "movies",
    movie.filename
  ).toString()
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
