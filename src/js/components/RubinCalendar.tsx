import React, { useEffect, useState } from "react"
import { CalendarData, Camera } from "./componentTypes"
import Calendar from "calendar"
import { monthNames, ymdToDateStr } from "../modules/utils"
import { homeUrl } from "../config"

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
}: {
  day: number
  dateStr: string
  calendarData: CalendarData[number][number]
  dayObs?: string | null
  selectedDate: Date
  cameraUrl: string
  noSeqNum?: boolean
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
  if (dateStringToDate(dateStr) == selectedDate) {
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
}: {
  year: number
  month: number
  isSelected: boolean
  calendarData: CalendarData
  cameraUrl: string
  noSeqNum: boolean
  calendarFrame: Calendar.Calendar
  selectedDate: Date
  dayObs?: string | null
}) => {
  return (
    <div className={`month ${isSelected ? "selected" : ""}`}>
      <h5 className="month-title">{monthNames[month - 1]}</h5>
      <div className="weekdays">
        {weekdays.map((day, index) => (
          <p key={index} className="day-name">
            {day}
          </p>
        ))}
      </div>
      <div className="days">
        {calendarFrame.monthDays(year, month - 1).map((week) =>
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

const dateStringToDate = (dateStr: string): Date => {
  const parts = dateStr.split("-")
  return new Date(
    parseInt(parts[0]),
    parseInt(parts[1]) - 1,
    parseInt(parts[2])
  )
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
}: {
  year: number
  yearToDisplay: number
  selectedDate: Date
  calendarData: CalendarData
  calendarFrame: Calendar.Calendar
  cameraUrl: string
  noSeqNum: boolean
  dayObs?: string | null
}) => {
  return (
    <div
      className={`year ${year == yearToDisplay ? "selected" : ""}`}
      id={`year-${year}`}
    >
      {Object.keys(calendarData[year])
        .map(Number)
        .sort((a, b) => a - b)
        .reverse()
        .map((month) => {
          const isSelected =
            year == yearToDisplay && month == selectedDate.getMonth() + 1
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

const RubinCalendar = ({
  selectedDate,
  initialCalendarData = {} as CalendarData,
  camera,
  locationName,
}: {
  selectedDate: string
  initialCalendarData: CalendarData
  camera: Camera
  locationName: string
}) => {
  const [yearToDisplay, setYearToDisplay] = useState(
    parseInt(selectedDate.split("-")[0])
  )
  const [calendarData, setCalendarData] = useState(initialCalendarData)
  const [dayObs, setDayObs] = useState(null)

  if (Object.keys(calendarData).length === 0) {
    return null
  }

  const sortedYears = Object.keys(calendarData)
    .map(Number)
    .sort((a, b) => a - b)
  const calFrame = new Calendar.Calendar(1)
  const cameraUrl = `${homeUrl}${locationName}/${camera.name}`
  const noSeqNum = camera.name === "allsky"

  const handleYearClick = (year: number) => {
    setYearToDisplay(year)
  }

  useEffect(() => {
    const yearEl = document.querySelector(".year.selected") as HTMLElement
    const monthEl = document.querySelector(".month.selected") as HTMLElement
    if (yearEl && monthEl) {
      yearEl.scrollLeft = monthEl.offsetLeft - yearEl.offsetLeft
    }
  }, [yearToDisplay])

  useEffect(() => {
    const handleCalendarEvent = (event: CustomEvent) => {
      const { dataType, data, datestamp } = event.detail
      if (dataType === "dayChange") {
        setDayObs(datestamp)
      }
      if (dataType === "latestMetadata" || dataType === "perDay") {
        const [year, month, day] = datestamp
          .split("-")
          .map((x: string) => parseInt(x))
        setCalendarData((prevCalendarData) => {
          const newCalendar = { ...prevCalendarData }
          if (!newCalendar[year]) {
            newCalendar[year] = {}
          }
          if (!newCalendar[year][month]) {
            newCalendar[year][month] = {}
          }
          if (noSeqNum) {
            newCalendar[year][month][day] = 1
          } else {
            const seqNum = parseInt(Object.keys(data)[0])
            newCalendar[year][month][day] = seqNum
          }
          return newCalendar
        })
        setDayObs(datestamp)
      }
    }
    window.addEventListener("calendar", handleCalendarEvent as EventListener)
    return () => {
      window.removeEventListener(
        "calendar",
        handleCalendarEvent as EventListener
      )
    }
  }, [])
  const yearClass = (year: number) => {
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
            selectedDate={dateStringToDate(selectedDate)}
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

export default RubinCalendar
