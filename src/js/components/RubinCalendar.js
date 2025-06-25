import React, { useEffect, useState } from "react"
import PropTypes from "prop-types"
import { calendarType, cameraType } from "./componentPropTypes"
import Calendar from "calendar"
import { monthNames, ymdToDateStr } from "../modules/utils"

const homeUrl = window.APP_DATA.homeUrl

const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

// Day component renders an individual day
const Day = ({
  day,
  dateStr,
  calendarData,
  dayObs,
  selectedDate,
  cameraUrl,
  noSeqNum,
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
  if (dateStr == selectedDate) {
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
  calendarData,
  cameraUrl,
  noSeqNum,
  calendarFrame,
  selectedDate,
  dayObs,
}) => {
  return (
    <div className={`month ${isSelected ? "selected" : ""}`}>
      <h5 className="month-title">{monthNames[month - 1]}</h5>
      <div className="weekdays">
        {weekdays.map((day, index) => (
          <p key={index} className="day-name">
            {day.substring(0, 3)}
          </p>
        ))}
      </div>
      <div className="days">
        {calendarFrame.monthDays(parseInt(year), month - 1).map((week) =>
          week.map((day, dayIndex) => {
            const dateStr = ymdToDateStr(year, month, day)
            return (
              <Day
                key={dateStr + dayIndex}
                dateStr={dateStr}
                day={day}
                calendarData={calendarData[year][month]}
                dayObs={dayObs}
                selectedDate={selectedDate}
                noSeqNum={noSeqNum}
                cameraUrl={cameraUrl}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
Month.propTypes = {
  year: PropTypes.string.isRequired,
  month: PropTypes.number.isRequired,
  isSelected: PropTypes.bool.isRequired,
  calendarData: PropTypes.object.isRequired,
  cameraUrl: PropTypes.string.isRequired,
  noSeqNum: PropTypes.bool.isRequired,
  calendarFrame: PropTypes.object.isRequired,
  selectedDate: PropTypes.string.isRequired,
  dayObs: PropTypes.string,
}

// Year component renders a year and its months
const Year = ({
  year,
  yearToDisplay,
  selectedDate,
  calendarData,
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
      {Object.keys(calendarData[year])
        .sort((a, b) => a - b)
        .reverse()
        .map((monthStr) => {
          const month = parseInt(monthStr)
          const isSelected =
            year == yearToDisplay && month == selectedDate.month
          return (
            <Month
              key={month}
              year={year}
              month={month}
              isSelected={isSelected}
              calendarData={calendarData}
              cameraUrl={cameraUrl}
              noSeqNum={noSeqNum}
              calendarFrame={calendarFrame}
              selectedDate={selectedDate}
              dayObs={dayObs}
            />
          )
        })}
    </div>
  )
}
Year.propTypes = {
  year: PropTypes.string.isRequired,
  yearToDisplay: PropTypes.string.isRequired,
  dayObs: PropTypes.string,
  selectedDate: PropTypes.string.isRequired,
  calendarData: calendarType.isRequired,
  calendarFrame: PropTypes.object.isRequired,
  cameraUrl: PropTypes.string.isRequired,
  noSeqNum: PropTypes.bool.isRequired,
}

const RubinCalendar = ({
  selectedDate,
  initialCalendarData = {},
  camera,
  locationName,
}) => {
  const [yearToDisplay, setYearToDisplay] = useState(selectedDate.split("-")[0])
  const [calendarData, setCalendarData] = useState(initialCalendarData)
  const [dayObs, setDayObs] = useState(null)

  if (Object.keys(calendarData).length === 0) {
    return null
  }

  const sortedYears = Object.keys(calendarData).sort((a, b) => a - b)
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
        setCalendarData((prevCalendarData) => {
          const newCalendar = { ...prevCalendarData }
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
  }, [])
  const yearClass = (year) => {
    return year == yearToDisplay ? "selected year-title" : "year-title"
  }
  return (
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
            year={yr}
            yearToDisplay={yearToDisplay}
            dayObs={dayObs}
            selectedDate={selectedDate}
            calendarData={calendarData}
            calendarFrame={calFrame}
            cameraUrl={cameraUrl}
            noSeqNum={noSeqNum}
          />
        ))}
      </div>
    </div>
  )
}
RubinCalendar.propTypes = {
  selectedDate: PropTypes.string.isRequired,
  initialCalendarData: calendarType.isRequired,
  camera: cameraType.isRequired,
  locationName: PropTypes.string.isRequired,
}

export default RubinCalendar
