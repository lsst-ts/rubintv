import React, { useEffect } from "react"
import Calendar from "calendar"

const RubinCalendar = ({ date, calendar, camera, locationName }) => {
  // Determine the year to display:
  const calFrame = new Calendar.Calendar(0)
  const sortedYears = Object.keys(calendar).sort()
  const yearToDisplay = sortedYears[sortedYears.length - 1]

  // Create camera URL (adjust as needed)
  const cameraUrl = `/camera/${locationName}/${camera.name}`

  // Flag for displaying count vs. asterisk:
  const noTotalSeq = camera.name === "allsky"

  useEffect(() => {
    const yearEl = document.querySelector(".year.current")
    const monthEl = document.querySelector(".month.current")
    if (yearEl && monthEl) {
      yearEl.scrollLeft = monthEl.offsetLeft - yearEl.offsetLeft
    }
  }, [yearToDisplay])

  return (
    <div>
      <div className="year-titles">
        <div className="year-button year-more"></div>
        <div className="year-title-viewbox">
          {[...sortedYears].reverse().map((yr) => (
            <p
              key={yr}
              className={`year-title ${yr == yearToDisplay ? "current" : ""}`}
              data-year={yr}
            >
              {yr}
            </p>
          ))}
        </div>
        <div className="year-button year-less"></div>
      </div>

      <div className="years">
        {[...sortedYears].reverse().map((yr) => (
          <div
            key={yr}
            className={`year ${yr == yearToDisplay ? "current" : ""}`}
            id={`year-${yr}`}
          >
            {
              // Sort months in descending order:
              [...Object.keys(calendar[yr]).sort()]
                .reverse()
                .map((monthStr) => {
                  const month = parseInt(monthStr, 10)
                  return (
                    <div
                      key={month}
                      className={`month ${
                        yr == yearToDisplay && month == date.month
                          ? "current"
                          : ""
                      }`}
                    >
                      <h5 className="month-title">{monthNames[month - 1]}</h5>
                      <div className="days">
                        {calFrame
                          .monthDays(parseInt(yr), month)
                          .map((week, weekIndex) =>
                            week.map((day, dayIndex) => {
                              if (day === 0) {
                                return (
                                  <p
                                    key={`${weekIndex}-${dayIndex}`}
                                    className="no-day"
                                  ></p>
                                )
                              }
                              if (
                                calendar[yr][month] &&
                                calendar[yr][month][day] !== undefined
                              ) {
                                const dateStr = `${yr}-${("0" + month).slice(
                                  -2
                                )}-${("0" + day).slice(-2)}`
                                return (
                                  <a
                                    key={`${weekIndex}-${dayIndex}`}
                                    className="day obs"
                                    href={`${cameraUrl}/date/${dateStr}`}
                                  >
                                    <span className="day_num">{day}</span>
                                    {!noTotalSeq ? (
                                      <span className="num_evs">
                                        ({calendar[yr][month][day]})
                                      </span>
                                    ) : (
                                      <span>*</span>
                                    )}
                                  </a>
                                )
                              } else {
                                return (
                                  <p
                                    key={`${weekIndex}-${dayIndex}`}
                                    className="day"
                                  >
                                    {day}
                                  </p>
                                )
                              }
                            })
                          )}
                      </div>
                    </div>
                  )
                })
            }
          </div>
        ))}
      </div>
    </div>
  )
}

export default RubinCalendar

const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]
