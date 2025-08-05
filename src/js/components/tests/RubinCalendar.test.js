import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, act, within } from "@testing-library/react"
import RubinCalendar from "../RubinCalendar"

/* global jest, describe, it, expect, beforeEach, beforeAll, afterEach */

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

// Mock utility functions
jest.mock("../../modules/utils", () => ({
  monthNames,
  ymdToDateStr: jest.fn((year, month, day) => {
    const monthStr = month.toString().padStart(2, "0")
    const dayStr = day.toString().padStart(2, "0")
    return `${year}-${monthStr}-${dayStr}`
  }),
}))

// Mock calendar module
jest.mock("calendar", () => ({
  Calendar: jest.fn().mockImplementation(() => ({
    monthDays: jest.fn((year, month) => {
      // Return a simple mock month structure (4 weeks with 7 days each)
      // This simulates the calendar structure for testing
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      const firstDayOfWeek = new Date(year, month, 1).getDay()
      const adjustedFirstDay = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1 // Convert Sunday=0 to Monday=0

      const weeks = []
      let currentWeek = []

      // Add empty days for the beginning of the month
      for (let i = 0; i < adjustedFirstDay; i++) {
        currentWeek.push(0)
      }

      // Add days of the month
      for (let day = 1; day <= daysInMonth; day++) {
        currentWeek.push(day)
        if (currentWeek.length === 7) {
          weeks.push(currentWeek)
          currentWeek = []
        }
      }

      // Add remaining days to complete the last week
      while (currentWeek.length > 0 && currentWeek.length < 7) {
        currentWeek.push(0)
      }
      if (currentWeek.length > 0) {
        weeks.push(currentWeek)
      }

      return weeks
    }),
    monthNames,
    yearNames: (startYear, endYear) => {
      const years = []
      for (let year = startYear; year <= endYear; year++) {
        years.push(year.toString())
      }
      return years
    },
  })),
}))

// Mock config
jest.mock("../../config", () => ({
  homeUrl: "http://test.com/",
}))

// Mock scrollIntoView for all elements to avoid TypeError in tests
beforeAll(() => {
  if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = jest.fn()
  }
})

describe("RubinCalendar Component", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [],
  }

  const mockCalendarData = {
    2024: {
      1: {
        15: 100,
        16: 101,
        20: 105,
      },
      2: {
        1: 150,
        5: 155,
      },
    },
    2023: {
      12: {
        25: 200,
        31: 210,
      },
    },
  }

  const defaultProps = {
    selectedDate: "2024-01-15",
    initialCalendarData: mockCalendarData,
    camera: mockCamera,
    locationName: "test-location",
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe("Basic Rendering", () => {
    it("renders calendar with provided data", () => {
      render(<RubinCalendar {...defaultProps} />)

      expect(screen.getAllByText("2024").length).toBeGreaterThan(0)
      expect(screen.getAllByText("2023").length).toBeGreaterThan(0)
      expect(screen.getAllByText("January").length).toBeGreaterThan(0)
      expect(screen.getAllByText("February").length).toBeGreaterThan(0)
    })

    it("renders null when no calendar data provided", () => {
      const { container } = render(
        <RubinCalendar {...defaultProps} initialCalendarData={{}} />
      )

      expect(container.firstChild).toBeNull()
    })

    it("renders weekday headers", () => {
      render(<RubinCalendar {...defaultProps} />)

      expect(screen.getAllByText(/Mon/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Tue/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Wed/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Thu/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Fri/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Sat/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/Sun/).length).toBeGreaterThan(0)
    })

    it("displays years in reverse chronological order", () => {
      render(<RubinCalendar {...defaultProps} />)

      const yearTitles = screen.getAllByText(/202[34]/)
      expect(yearTitles[0]).toHaveTextContent("2024")
      expect(yearTitles[1]).toHaveTextContent("2023")
    })

    it("displays months in reverse chronological order within a year", () => {
      render(<RubinCalendar {...defaultProps} />)

      const monthElements = document.querySelectorAll(".month h5")
      const monthTexts = Array.from(monthElements).map((el) => el.textContent)

      // Should show February before January for 2024
      const febIndex = monthTexts.indexOf("February")
      const janIndex = monthTexts.indexOf("January")
      expect(febIndex).toBeLessThan(janIndex)
    })
  })

  describe("Day Component", () => {
    it("renders days with observation data as links", () => {
      render(<RubinCalendar {...defaultProps} />)

      const day15Links = screen.getAllByRole("link", { name: /15/ })
      const day15Link = day15Links.find(
        (el) =>
          el.getAttribute("href") ===
          "http://test.com/test-location/testcam/date/2024-01-15"
      )
      expect(day15Link).toBeInTheDocument()
      expect(day15Link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/date/2024-01-15"
      )
      expect(day15Link).toHaveClass("day", "obs")
      expect(screen.getAllByText("(100)")[0]).toBeInTheDocument()
    })

    it("renders days without data as plain text", () => {
      render(<RubinCalendar {...defaultProps} />)

      const januaryMonth = screen.getAllByText("January")[0].closest(".month")
      const day2InJanuary = within(januaryMonth).getByText("2")

      expect(day2InJanuary.closest("a")).toBeNull()
      expect(day2InJanuary.closest("p")).toHaveClass("day")
    })

    it("marks selected date with selected class", () => {
      render(<RubinCalendar {...defaultProps} />)

      const januaryMonth = screen.getAllByText("January")[0].closest(".month")
      const selectedDaySpan = within(januaryMonth).getByText("15")
      const selectedDay = selectedDaySpan.closest("a")
      expect(selectedDay).toBeInTheDocument()

      expect(selectedDay).toHaveClass("selected")

      const selectedBorder = selectedDay.querySelector(".selected-border")
      expect(selectedBorder).toBeInTheDocument()
    })

    it("marks today with today class when dayObs matches", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "dayChange",
            datestamp: "2024-01-16",
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const todayElement = screen.getByRole("link", { name: /16/ })
      expect(todayElement).toHaveClass("today")
    })

    describe("Allsky Camera Behavior", () => {
      it("shows asterisk for allsky camera instead of sequence numbers", () => {
        const allskyCamera = { ...mockCamera, name: "allsky" }

        render(<RubinCalendar {...defaultProps} camera={allskyCamera} />)

        const daysWithData = screen
          .getAllByRole("link")
          .filter((link) => link.classList.contains("obs"))

        // Each day with data should show asterisk instead of sequence number
        daysWithData.forEach((dayLink) => {
          // Look for asterisk text content anywhere in the link
          expect(dayLink).toHaveTextContent("*")
          // Ensure it doesn't have parentheses (which would indicate sequence numbers)
          expect(dayLink.textContent).not.toMatch(/\(\d+\)/)
        })
      })

      it("shows asterisk for allsky camera when new data arrives", () => {
        const allskyCamera = { ...mockCamera, name: "allsky" }

        render(<RubinCalendar {...defaultProps} camera={allskyCamera} />)

        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "2024-01-25",
              data: { 250: { some: "metadata" } },
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        const januaryMonth = screen.getAllByText("January")[0].closest(".month")
        const selectedDaySpan = within(januaryMonth).getByText("25")
        const newDay = selectedDaySpan.closest("a")
        const sequenceSpan = newDay.querySelector(".has-events")
        expect(sequenceSpan).toHaveTextContent("*")
      })

      it("shows sequence numbers for non-allsky cameras", () => {
        const regularCamera = { ...mockCamera, name: "regular_cam" }

        render(<RubinCalendar {...defaultProps} camera={regularCamera} />)

        const januaryMonth = screen.getAllByText("January")[0].closest(".month")
        const selectedDaySpan = within(januaryMonth).getByText("15")
        const dayWithData = selectedDaySpan.closest("a")
        const sequenceSpan = dayWithData.querySelector(".has-events")
        expect(sequenceSpan).toHaveTextContent("(100)")
      })
    })

    describe("Calendar Data Structure", () => {
      it("handles non-sequential sequence numbers", () => {
        const sparseData = {
          2024: {
            1: {
              15: 100,
              16: 200,
              17: 500,
            },
          },
        }

        render(
          <RubinCalendar {...defaultProps} initialCalendarData={sparseData} />
        )

        expect(screen.getByText("(100)")).toBeInTheDocument()
        expect(screen.getByText("(200)")).toBeInTheDocument()
        expect(screen.getByText("(500)")).toBeInTheDocument()
      })

      it("handles zero sequence numbers", () => {
        const zeroData = {
          2024: {
            1: {
              15: 0,
            },
          },
        }

        render(
          <RubinCalendar {...defaultProps} initialCalendarData={zeroData} />
        )

        const dayWithData = screen.getByRole("link", { name: /15/ })
        expect(dayWithData).toHaveClass("obs")
        expect(screen.getByText("(0)")).toBeInTheDocument()
      })

      it("handles string sequence numbers", () => {
        const stringData = {
          2024: {
            1: {
              15: "abc123",
            },
          },
        }

        render(
          <RubinCalendar {...defaultProps} initialCalendarData={stringData} />
        )

        expect(screen.getByText("(abc123)")).toBeInTheDocument()
      })
    })

    describe("Calendar Navigation", () => {
      it("scrolls to selected month", () => {
        render(<RubinCalendar {...defaultProps} selectedDate={"2023-12-25"} />)
        const year2023 = document.getElementById("year-2023")
        const monthDecember = screen
          .getAllByText("December")[0]
          .closest(".month")
        const scrollIntoView = jest.spyOn(monthDecember, "scrollIntoView")
        // Should attempt to scroll to the selected month
        expect(scrollIntoView).toHaveBeenCalled()
      })

      it("maintains scroll position when data updates", () => {
        const { container } = render(<RubinCalendar {...defaultProps} />)

        const initialScrollTop = container.scrollTop

        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "2024-01-25",
              data: { 250: { some: "metadata" } },
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        // Scroll position should not change on data updates
        expect(container.scrollTop).toBe(initialScrollTop)
      })
    })

    describe("Event Data Validation", () => {
      it("handles events with null data", () => {
        render(<RubinCalendar {...defaultProps} />)

        expect(() => {
          act(() => {
            const calendarEvent = new CustomEvent("calendar", {
              detail: {
                dataType: "latestMetadata",
                datestamp: "2024-01-31",
                data: null,
              },
            })
            window.dispatchEvent(calendarEvent)
          })
        }).not.toThrow()
      })

      it("handles events with undefined properties", () => {
        render(<RubinCalendar {...defaultProps} />)

        expect(() => {
          act(() => {
            const calendarEvent = new CustomEvent("calendar", {
              detail: {
                dataType: "latestMetadata",
                // Missing datestamp
                data: { 100: {} },
              },
            })
            window.dispatchEvent(calendarEvent)
          })
        }).not.toThrow()
      })

      it("handles events with empty detail object", () => {
        render(<RubinCalendar {...defaultProps} />)

        expect(() => {
          act(() => {
            const calendarEvent = new CustomEvent("calendar", {
              detail: {},
            })
            window.dispatchEvent(calendarEvent)
          })
        }).not.toThrow()
      })
    })

    describe("Month/Year Boundaries", () => {
      it("handles data for February 29th in leap years", () => {
        const leapYearData = {
          2024: {
            2: {
              29: 100,
            },
          },
        }

        render(
          <RubinCalendar {...defaultProps} initialCalendarData={leapYearData} />
        )

        const feb29Link = screen.getByRole("link", { name: /29/ })
        expect(feb29Link).toBeInTheDocument()
        expect(feb29Link).toHaveAttribute(
          "href",
          "http://test.com/test-location/testcam/date/2024-02-29"
        )
      })

      it("handles data for December 31st", () => {
        const yearEndData = {
          2024: {
            12: {
              31: 365,
            },
          },
        }

        render(
          <RubinCalendar {...defaultProps} initialCalendarData={yearEndData} />
        )

        expect(screen.getByText("December")).toBeInTheDocument()
        const dec31Link = screen.getByRole("link", { name: /31/ })
        expect(dec31Link).toBeInTheDocument()
      })

      it("handles transition between years correctly", () => {
        render(<RubinCalendar {...defaultProps} />)

        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "2023-12-31",
              data: { 999: { end_of_year: true } },
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "2024-01-01",
              data: { 1: { start_of_year: true } },
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        // Both dates should be present
        const dec31Link = screen.getByRole("link", {
          name: /31/,
        })
        const jan1Link = screen.getByRole("link", {
          name: /1 \(1\)/,
        })

        expect(dec31Link).toBeInTheDocument()
        expect(jan1Link).toBeInTheDocument()
      })
    })

    describe("Visual State Management", () => {
      it("removes today class when day changes", () => {
        render(<RubinCalendar {...defaultProps} />)

        // Set initial today
        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "dayChange",
              datestamp: "2024-01-16",
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        const firstToday = screen.getByRole("link", { name: /16/ })
        expect(firstToday).toHaveClass("today")

        // Change to different day
        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "dayChange",
              datestamp: "2024-01-20",
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        expect(firstToday).not.toHaveClass("today")
        const allDayLinks = screen.getAllByRole("link", { name: /20/ })
        // Find the link for 2024-01-20 specifically
        const newToday = allDayLinks.find(
          (el) =>
            el.getAttribute("href") ===
            "http://test.com/test-location/testcam/date/2024-01-20"
        )
        expect(newToday).toHaveClass("today")
      })

      it("maintains selected state independently of today state", () => {
        render(<RubinCalendar {...defaultProps} selectedDate="2024-01-15" />)

        const allDayLinks = screen.getAllByRole("link", { name: /15/ })
        const selectedDay = allDayLinks.find(
          (el) =>
            el.getAttribute("href") ===
            "http://test.com/test-location/testcam/date/2024-01-15"
        )
        expect(selectedDay).toHaveClass("selected")

        // Set today to different day
        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "dayChange",
              datestamp: "2024-01-16",
            },
          })
          window.dispatchEvent(calendarEvent)
        })

        // Selected day should still be selected
        expect(selectedDay).toHaveClass("selected")

        const todayDay = screen.getByRole("link", { name: /16/ })
        expect(todayDay).toHaveClass("today")
        expect(todayDay).not.toHaveClass("selected")
      })
    })

    it("marks selected month with selected class", () => {
      render(<RubinCalendar {...defaultProps} />)

      const januaryMonth = screen.getAllByText("January")[0].closest(".month")
      expect(januaryMonth).toHaveClass("selected")

      const februaryMonth = screen.getAllByText("February")[0].closest(".month")
      expect(februaryMonth).not.toHaveClass("selected")
    })

    it("renders all days for the month", () => {
      render(<RubinCalendar {...defaultProps} />)

      // January should have days 1-31
      for (let day = 1; day <= 31; day++) {
        expect(screen.getAllByText(day.toString()).length).toBeGreaterThan(0)
      }
    })
  })

  describe("Year Component", () => {
    it("renders year with correct structure", () => {
      render(<RubinCalendar {...defaultProps} />)

      const year2024 = document.getElementById("year-2024")
      expect(year2024).toBeInTheDocument()
      expect(year2024).toHaveClass("year", "selected")

      const year2023 = document.getElementById("year-2023")
      expect(year2023).toBeInTheDocument()
      expect(year2023).toHaveClass("year")
      expect(year2023).not.toHaveClass("selected")
    })

    it("contains months for the year", () => {
      render(<RubinCalendar {...defaultProps} />)

      const year2024 = document.getElementById("year-2024")
      const months = year2024.querySelectorAll(".month")
      expect(months.length).toBe(2) // January and February
    })
  })

  describe("Year Selection", () => {
    it("changes displayed year when year title is clicked", () => {
      render(<RubinCalendar {...defaultProps} />)

      const year2023Title = screen.getAllByText("2023")[0] // Year title
      fireEvent.click(year2023Title)

      expect(year2023Title).toHaveClass("selected")

      const year2024Title = screen.getAllByText("2024")[0]
      expect(year2024Title).not.toHaveClass("selected")
    })

    it("updates year display and scrolls to selected month", () => {
      // Mock scrollLeft property
      Object.defineProperty(HTMLElement.prototype, "scrollLeft", {
        writable: true,
        value: 0,
      })
      Object.defineProperty(HTMLElement.prototype, "offsetLeft", {
        writable: true,
        value: 100,
      })

      render(<RubinCalendar {...defaultProps} />)

      const year2023Title = screen.getAllByText("2023")[0]
      fireEvent.click(year2023Title)

      // Should trigger scroll effect
      expect(year2023Title).toHaveClass("selected")
    })
  })

  describe("Calendar Event Handling", () => {
    it("handles dayChange events", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "dayChange",
            datestamp: "2024-01-20",
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const allDayLinks = screen.getAllByRole("link", { name: /20/ })
      const todayElement = allDayLinks.find(
        (el) =>
          el.getAttribute("href") ===
          "http://test.com/test-location/testcam/date/2024-01-20"
      )
      expect(todayElement).toHaveClass("today")
    })

    it("handles latestMetadata events and updates calendar data", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "latestMetadata",
            datestamp: "2024-01-25",
            data: { 250: { some: "metadata" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      // New day should now have data
      const januaryMonth = screen.getAllByText("January")[0].closest(".month")
      const selectedDaySpan = within(januaryMonth).getByText("25")
      const newDay = selectedDaySpan.closest("a")
      expect(newDay).toBeInTheDocument()
      expect(newDay).toHaveClass("obs")
      expect(screen.getAllByText("(250)")[0]).toBeInTheDocument()
    })

    it("handles perDay events and updates calendar data", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "perDay",
            datestamp: "2024-02-10",
            data: { 300: { some: "perday_data" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const februaryMonth = screen.getAllByText("February")[0].closest(".month")
      const selectedDaySpan = within(februaryMonth).getByText("10")
      const newDay = selectedDaySpan.closest("a")
      expect(newDay).toBeInTheDocument()
      expect(screen.getAllByText("(300)")[0]).toBeInTheDocument()
    })

    it("handles events for allsky camera with asterisk display", () => {
      const allskyCamera = { ...mockCamera, name: "allsky" }

      render(<RubinCalendar {...defaultProps} camera={allskyCamera} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "latestMetadata",
            datestamp: "2024-01-30",
            data: { 400: { some: "metadata" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const newDay = screen.getByRole("link", { name: /30/ })
      expect(newDay.querySelector(".has-events")).toHaveTextContent("*")
    })

    it("creates new year/month structure when needed", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "latestMetadata",
            datestamp: "2025-03-15",
            data: { 500: { some: "metadata" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      // Should create new year and month
      expect(screen.getAllByText("2025")[0]).toBeInTheDocument()
      expect(screen.getAllByText("March")[0]).toBeInTheDocument()

      const marchMonth = screen.getAllByText("March")[0].closest(".month")
      expect(marchMonth).toBeInTheDocument()
      expect(marchMonth).toHaveClass("month")
      const newDay = within(marchMonth).getByRole("link", { name: /15/ })
      expect(newDay).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/date/2025-03-15"
      )
    })

    it("ignores events with unrecognized dataType", () => {
      render(<RubinCalendar {...defaultProps} />)

      const initialDays = screen.getAllByRole("link")
      const initialCount = initialDays.length

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "unknown",
            datestamp: "2024-01-31",
            data: { 600: { some: "data" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const finalDays = screen.getAllByRole("link")
      expect(finalDays.length).toBe(initialCount)
    })
  })

  describe("URL Generation", () => {
    it("generates correct URLs for day links", () => {
      render(<RubinCalendar {...defaultProps} />)

      const allDayLinks = screen.getAllByRole("link", { name: /15/ })
      const day15Link = allDayLinks.find(
        (el) =>
          el.getAttribute("href") ===
          "http://test.com/test-location/testcam/date/2024-01-15"
      )
      expect(day15Link).toBeInTheDocument()
      expect(day15Link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/date/2024-01-15"
      )

      const day16Link = screen.getByRole("link", { name: /16/ })
      expect(day16Link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/date/2024-01-16"
      )
    })

    it("generates URLs with different camera and location names", () => {
      render(
        <RubinCalendar
          {...defaultProps}
          camera={{ ...mockCamera, name: "othercam" }}
          locationName="other-location"
        />
      )

      const allDayLinks = screen.getAllByRole("link", { name: /15/ })
      const day15Link = allDayLinks.find(
        (el) =>
          el.getAttribute("href") ===
          "http://test.com/other-location/othercam/date/2024-01-15"
      )
      expect(day15Link).toBeInTheDocument()
    })
  })

  describe("Date Formatting", () => {
    it("calls ymdToDateStr with correct parameters", () => {
      const { ymdToDateStr } = require("../../modules/utils")

      render(<RubinCalendar {...defaultProps} />)

      expect(ymdToDateStr).toHaveBeenCalledWith(2024, 1, 15)
      expect(ymdToDateStr).toHaveBeenCalledWith(2024, 1, 16)
      expect(ymdToDateStr).toHaveBeenCalledWith(2024, 1, 20)
    })

    it("handles date string parsing correctly", () => {
      render(<RubinCalendar {...defaultProps} selectedDate="2023-12-25" />)

      const year2023 = document.getElementById("year-2023")
      expect(year2023).toHaveClass("selected")

      const decemberMonth = screen.getAllByText("December")[0].closest(".month")
      expect(decemberMonth).toHaveClass("selected")

      const day25Link = screen.getByRole("link", { name: /25/ })
      expect(day25Link).toHaveClass("selected")
    })
  })

  describe("Component Cleanup", () => {
    it("removes calendar event listener on unmount", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(<RubinCalendar {...defaultProps} />)

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "calendar",
        expect.any(Function)
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "calendar",
        expect.any(Function)
      )

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })
  })

  describe("Edge Cases", () => {
    it("handles empty calendar data gracefully", () => {
      render(<RubinCalendar {...defaultProps} initialCalendarData={{}} />)

      expect(screen.queryByText("2024")).not.toBeInTheDocument()
    })

    it("handles malformed date strings", () => {
      expect(() => {
        render(<RubinCalendar {...defaultProps} selectedDate="invalid-date" />)
      }).not.toThrow()
    })

    it("handles calendar data with missing months", () => {
      const sparseCalendarData = {
        2024: {
          1: { 15: 100 },
          // Missing month 2
          3: { 10: 200 },
        },
      }

      render(
        <RubinCalendar
          {...defaultProps}
          initialCalendarData={sparseCalendarData}
        />
      )

      expect(screen.getAllByText("January")[0]).toBeInTheDocument()
      expect(screen.getAllByText("March")[0]).toBeInTheDocument()
      expect(screen.queryByText("February")).not.toBeInTheDocument()
    })

    it("handles events with malformed datestamp", () => {
      render(<RubinCalendar {...defaultProps} />)

      expect(() => {
        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "invalid-date",
              data: { 100: {} },
            },
          })
          window.dispatchEvent(calendarEvent)
        })
      }).not.toThrow()
    })

    it("handles events with missing data", () => {
      render(<RubinCalendar {...defaultProps} />)

      expect(() => {
        act(() => {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: "2024-01-31",
              data: {},
            },
          })
          window.dispatchEvent(calendarEvent)
        })
      }).not.toThrow()
    })

    it("handles very large sequence numbers", () => {
      render(<RubinCalendar {...defaultProps} />)

      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "latestMetadata",
            datestamp: "2024-01-31",
            data: { 999999999: { some: "data" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const newDay = screen.getByRole("link", { name: /31/ })
      expect(screen.getAllByText("(999999999)")[0]).toBeInTheDocument()
    })
  })

  describe("Accessibility", () => {
    it("provides accessible day links", () => {
      render(<RubinCalendar {...defaultProps} />)

      const dayLinks = screen.getAllByRole("link")
      dayLinks.forEach((link) => {
        expect(link).toHaveAttribute("href")
      })
    })

    it("has proper heading structure", () => {
      render(<RubinCalendar {...defaultProps} />)

      const monthHeadings = screen.getAllByRole("heading", { level: 5 })
      expect(monthHeadings.length).toBeGreaterThan(0)

      monthHeadings.forEach((heading) => {
        expect(heading).toHaveTextContent(/January|February|December/)
      })
    })

    it("provides tooltips for days without data", () => {
      render(<RubinCalendar {...defaultProps} />)

      // Find a day without data (should be a <p> element)
      const dayWithoutDataElements = screen.getAllByText("1")
      const dayWithoutData = dayWithoutDataElements[0].closest("p")
      expect(dayWithoutData).toHaveAttribute("title", "today: no data yet")
    })
  })

  describe("Performance", () => {
    it("handles large calendar datasets efficiently", () => {
      const largeCalendarData = {}

      // Create data for multiple years with many days
      for (let year = 2020; year <= 2024; year++) {
        largeCalendarData[year] = {}
        for (let month = 1; month <= 12; month++) {
          largeCalendarData[year][month] = {}
          for (let day = 1; day <= 28; day++) {
            largeCalendarData[year][month][day] = day * 10
          }
        }
      }

      const renderStart = performance.now()
      render(
        <RubinCalendar
          {...defaultProps}
          initialCalendarData={largeCalendarData}
        />
      )
      const renderEnd = performance.now()

      // Rendering should complete in reasonable time (< 1000ms)
      expect(renderEnd - renderStart).toBeLessThan(1000)

      // Should still show all years
      expect(screen.getAllByText("2024")[0]).toBeInTheDocument()
      expect(screen.getAllByText("2020")[0]).toBeInTheDocument()
    })

    it("handles rapid event updates efficiently", () => {
      render(<RubinCalendar {...defaultProps} />)

      const eventStart = performance.now()

      act(() => {
        // Send many rapid events
        for (let i = 1; i <= 50; i++) {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: `2024-01-${i.toString().padStart(2, "0")}`,
              data: { [i]: { some: "data" } },
            },
          })
          window.dispatchEvent(calendarEvent)
        }
      })

      const eventEnd = performance.now()

      // Events should process quickly
      expect(eventEnd - eventStart).toBeLessThan(500)
    })
  })

  describe("Integration Tests", () => {
    it("completes full user interaction workflow", () => {
      render(<RubinCalendar {...defaultProps} />)

      // 1. Initial state
      expect(screen.getAllByText("2024")[0]).toHaveClass("selected")
      expect(screen.getAllByText("January")[0].closest(".month")).toHaveClass(
        "selected"
      )

      // 2. Change year
      const year2023 = screen.getAllByText("2023")[0]
      fireEvent.click(year2023)
      expect(year2023).toHaveClass("selected")

      // 3. Receive calendar event
      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "dayChange",
            datestamp: "2023-12-31",
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const todayElement = screen.getByRole("link", { name: /31/ })
      expect(todayElement).toHaveClass("today")

      // 4. Add new data via event
      act(() => {
        const calendarEvent = new CustomEvent("calendar", {
          detail: {
            dataType: "latestMetadata",
            datestamp: "2023-12-30",
            data: { 999: { new: "data" } },
          },
        })
        window.dispatchEvent(calendarEvent)
      })

      const newDataDay = screen.getByRole("link", { name: /30/ })
      expect(newDataDay).toHaveClass("obs")
      expect(screen.getAllByText("(999)")[0]).toBeInTheDocument()
    })

    it("maintains state consistency across multiple operations", () => {
      render(<RubinCalendar {...defaultProps} />)

      // Track initial link count
      const initialLinks = screen.getAllByRole("link")
      const initialCount = initialLinks.length

      // Add data to multiple days
      act(() => {
        for (let day = 25; day <= 31; day++) {
          const calendarEvent = new CustomEvent("calendar", {
            detail: {
              dataType: "latestMetadata",
              datestamp: `2024-01-${day}`,
              data: { [day * 10]: { some: "data" } },
            },
          })
          window.dispatchEvent(calendarEvent)
        }
      })

      // Should have more links now
      const finalLinks = screen.getAllByRole("link")
      expect(finalLinks.length).toBeGreaterThan(initialCount)

      // All new days should be observable
      for (let day = 25; day <= 31; day++) {
        const dayLink = screen.getByRole("link", {
          name: new RegExp(day.toString()),
        })
        expect(dayLink).toHaveClass("obs")
      }
    })
  })
})
