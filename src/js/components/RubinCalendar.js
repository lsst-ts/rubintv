import React, { StrictMode, useEffect, useState } from "react"
import Calendar from "calendar"
import { monthNames, ymdToDateStr } from "../modules/utils"

const homeUrl = window.APP_DATA.homeUrl

// Day component renders an individual day
const Day = ({
  day,
  dateStr,
  cameraUrl,
  noSeqNum,
  calendarData,
  date,
  dayObs,
}) => {
  let hasData = false
  let isSelected = false
  let currentDayClassList = ["day"]
  if (calendarData && calendarData[day] !== undefined) {
    hasData = true
    currentDayClassList.push("obs")
  }
  if (dayObs === dateStr) {
    currentDayClassList.push("today")
  }
  if (dateStr == date) {
    isSelected = true
    currentDayClassList.push("selected")
  }
  const currentDayClass = currentDayClassList.join(" ")

  if (day === 0) {
    return <p className="no-day"></p>
  }

  if (hasData) {
    return (
      <a className={currentDayClass} href={`${cameraUrl}/date/${dateStr}`}>
        <span className="day_num">{day}</span>
        {!noSeqNum ? (
          <span className="num_evs">({calendarData[day]})</span>
        ) : (
          <span>*</span>
        )}
        {isSelected && <div className="selected-border"></div>}
      </a>
    )
  }

  return (
    <p className={currentDayClass} title="today: no data yet">
      {day}
    </p>
  )
}

// Month component renders a month and its days
const Month = ({
  year,
  month,
  isSelected,
  calendar,
  cameraUrl,
  noSeqNum,
  calendarFrame,
  date,
  dayObs,
}) => {
  return (
    <div className={`month ${isSelected ? "selected" : ""}`}>
      <h5 className="month-title">{monthNames[month - 1]}</h5>
      <div className="days">
        {calendarFrame.monthDays(parseInt(year), month - 1).map((week) =>
          week.map((day, dayIndex) => {
            const dateStr = ymdToDateStr(year, month, day)
            return (
              <Day
                key={dateStr + dayIndex}
                day={day}
                dateStr={dateStr}
                cameraUrl={cameraUrl}
                noSeqNum={noSeqNum}
                calendarData={calendar[year][month]}
                date={date}
                dayObs={dayObs}
              />
            )
          })
        )}
      </div>
    </div>
  )
}

// Year component renders a year and its months
const Year = ({
  year,
  yearToDisplay,
  date,
  calendar,
  calendarFrame,
  cameraUrl,
  noSeqNum,
  dayObs,
}) => {
  return (
    <div
      className={`year ${year == yearToDisplay ? "selected" : ""}`}
      id={`year-${year}`}
    >
      {Object.keys(calendar[year])
        .sort((a, b) => a - b)
        .reverse()
        .map((monthStr) => {
          const month = parseInt(monthStr)
          const isSelected = year == yearToDisplay && month == date.month
          return (
            <Month
              key={month}
              year={year}
              month={month}
              isSelected={isSelected}
              calendar={calendar}
              cameraUrl={cameraUrl}
              noSeqNum={noSeqNum}
              calendarFrame={calendarFrame}
              date={date}
              dayObs={dayObs}
            />
          )
        })}
    </div>
  )
}

const RubinCalendar = ({ date, initialCalendar, camera, locationName }) => {
  const [yearToDisplay, setYearToDisplay] = useState(date.split("-")[0])
  const [calendar, setCalendar] = useState(initialCalendar)
  const [dayObs, setDayObs] = useState(null)

  const sortedYears = Object.keys(calendar).sort((a, b) => a - b)
  const calFrame = new Calendar.Calendar(1)
  const cameraUrl = `${homeUrl}${locationName}/${camera.name}`
  const noSeqNum = camera.name === "allsky"

  const handleYearClick = (year) => {
    setYearToDisplay(year)
  }

  useEffect(() => {
    const yearEl = document.querySelector(".year.selected")
    const monthEl = document.querySelector(".month.selected")
    if (yearEl && monthEl) {
      yearEl.scrollLeft = monthEl.offsetLeft - yearEl.offsetLeft
    }
  }, [yearToDisplay])

  useEffect(() => {
    const handleCalendarEvent = (event) => {
      const { dataType, data, datestamp } = event.detail
      if (dataType === "dayChange") {
        setDayObs(datestamp)
      }
      if (dataType === "latestMetadata") {
        const [year, month, day] = datestamp.split("-").map((x) => parseInt(x))
        const seqNum = parseInt(Object.keys(data)[0])
        setCalendar((prevCalendar) => {
          const newCalendar = { ...prevCalendar }
          if (!newCalendar[year]) {
            newCalendar[year] = {}
          }
          if (!newCalendar[year][month]) {
            newCalendar[year][month] = {}
          }
          newCalendar[year][month][day] = seqNum
          return newCalendar
        })
        setDayObs(datestamp)
      }
    }
    window.addEventListener("calendar", handleCalendarEvent)
    return () => {
      window.removeEventListener("calendar", handleCalendarEvent)
    }
  })
  const yearClass = (year) => {
    return year == yearToDisplay ? "selected year-title" : "year-title"
  }
  return (
    <StrictMode>
      <div>
        <div className="year-titles">
          <div className="year-button year-more"></div>
          <div className="year-title-viewbox">
            {[...sortedYears].reverse().map((yr) => (
              <p
                key={yr}
                className={yearClass(yr)}
                data-year={yr}
                onClick={() => handleYearClick(yr)}
              >
                {yr}
              </p>
            ))}
          </div>
          <div className="year-button year-less"></div>
        </div>

        <div className="years">
          {[...sortedYears].reverse().map((yr) => (
            <Year
              key={yr}
              dayObs={dayObs}
              year={yr}
              yearToDisplay={yearToDisplay}
              date={date}
              calendar={calendar}
              calendarFrame={calFrame}
              cameraUrl={cameraUrl}
              noSeqNum={noSeqNum}
            />
          ))}
        </div>
      </div>
    </StrictMode>
  )
}

export default RubinCalendar
