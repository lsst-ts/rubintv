import React, { useState, useEffect, useRef } from "react"
import RubinCalendar from "./RubinCalendar"
import { getMediaProxyUrl, getHistoricalData } from "../modules/utils"
import { AllSkyProps, AllSkyMediaProps, ExposureEvent } from "./componentTypes"

type EL = EventListener

export default function AllSky({
  initialDate,
  isHistorical,
  locationName,
  camera,
  calendar,
}: AllSkyProps) {
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
        try {
          const { perDay } = JSON.parse(json)
          if (!perDay || Object.keys(perDay).length === 0) {
            console.error("No perDay data found for", date)
            return
          }
          setPerDayData(perDay)
        } catch (error) {
          console.error("Error parsing historical data JSON:", error)
          console.error("Received data:", json)
        }
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
          <AllSkyStill
            details={perDayData.stills}
            locationName={locationName}
          />
        )}
        <AllSkyMovie details={perDayData.movies} locationName={locationName} />
      </div>
    </>
  )
}

function AllSkyStill({ details: still, locationName }: AllSkyMediaProps) {
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
        <a target="_blank" rel="noreferrer" href={imgUrl}>
          <img className="resp" src={imgUrl} />
        </a>
        <div className="desc">{still.filename}</div>
      </div>
    </section>
  )
}

function AllSkyMovie({ details: movie, locationName }: AllSkyMediaProps) {
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
