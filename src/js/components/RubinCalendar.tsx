import React, { useEffect, useState } from "react"
import {
  RubinCalendarProps,
  CalendarYearProps,
  CalendarMonthProps,
  CalendarDayProps,
  CalendarData,
} from "./componentTypes"
import * as Calendar from "calendar"
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
}: CalendarDayProps) => {
  let hasData = false
  let isSelected = false
  const currentDayClassList = ["day"]
  if (calendarData?.[day] !== undefined) {
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
          <span className="has-events num-events">({calendarData[day]})</span>
        ) : (
          <span className="has-events">*</span>
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
}: CalendarMonthProps) => {
  const selectedDateStr = ymdToDateStr(
    selectedDate.getFullYear(),
    // 1 is added to the month as Date months are zero-indexed
    selectedDate.getMonth() + 1,
    selectedDate.getDate()
  )
  return (
    <div className={`month ${isSelected ? "selected" : ""}`}>
      {/* 1 is subtracted from the month as monthNames are zero-indexed */}
      <h5 className="month-title">{monthNames[month - 1]}</h5>
      <div className="weekdays">
        {weekdays.map((day, index) => (
          <p key={index} className="day-name">
            {day}
          </p>
        ))}
      </div>
      <div className="days">
        {/* again, 1 is added to the month as Calendar.Calendar months are
        zero-indexed */}
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
                selectedDate={selectedDateStr}
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
    // One month is subtracted from the month as Date months are zero-indexed
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
}: CalendarYearProps) => {
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
          // 1 is added to the month so that it represents the actual month number
          // i.e. January is 1, February is 2, etc.
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
}: RubinCalendarProps) => {
  const [yearToDisplay, setYearToDisplay] = useState(
    parseInt(selectedDate.split("-")[0], 10)
  )
  const [calendarData, setCalendarData] = useState(initialCalendarData)
  const [dayObs, setDayObs] = useState(null)

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
      monthEl.scrollIntoView({ behavior: "instant", block: "nearest" })
    }
  }, [yearToDisplay])

  useEffect(() => {
    const handleCalendarEvent = (event: CustomEvent) => {
      const { dataType, data, datestamp } = event.detail
      if (!dataType || !datestamp) {
        console.warn("Invalid calendar event data", event.detail)
        return
      }
      if (dataType === "dayChange") {
        setDayObs(datestamp)
      }
      if (dataType === "latestMetadata" || dataType === "perDay") {
        const updatedCalendarData = updateCalendarData(
          calendarData,
          datestamp,
          data
        )
        setCalendarData(updatedCalendarData)
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
  }, [calendarData])

  if (Object.keys(calendarData).length === 0) {
    return null
  }

  const yearClass = (year: number) => {
    return year == yearToDisplay ? "selected year-title" : "year-title"
  }
  return (
    <>
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
    </>
  )
}

function updateCalendarData(
  calendarData: CalendarData,
  datestamp: string,
  data: Record<string, unknown>
): CalendarData {
  if (!datestamp) return calendarData

  const [yearStr, monthStr, dayStr] = datestamp.split("-")
  const year = parseInt(yearStr, 10)
  const month = parseInt(monthStr, 10)
  const day = parseInt(dayStr, 10)

  if (isNaN(year) || isNaN(month) || isNaN(day)) return calendarData

  if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
    return calendarData
  }

  // Find the highest sequence number (as string, but compare numerically if possible)
  let maxSeq: number | string | null = null
  Object.keys(data).forEach((seq) => {
    if (
      maxSeq === null ||
      Number(seq) > Number(maxSeq) ||
      (isNaN(Number(seq)) && seq > maxSeq)
    ) {
      maxSeq = seq
    }
  })
  if (maxSeq === null) return calendarData

  const newCalendarData = { ...calendarData }
  if (!newCalendarData[year]) newCalendarData[year] = {}
  if (!newCalendarData[year][month]) newCalendarData[year][month] = {}
  newCalendarData[year][month] = { ...newCalendarData[year][month] }

  // Always convert to number for CalendarData interface compliance
  const seqAsNumber = Number(maxSeq)
  newCalendarData[year][month][day] = isNaN(seqAsNumber) ? 0 : seqAsNumber

  return newCalendarData
}

export default RubinCalendar
