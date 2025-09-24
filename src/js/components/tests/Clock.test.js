import React from "react"
import { render, screen, act } from "@testing-library/react"
import "@testing-library/jest-dom"
import Clock, { TimeSinceLastImageClock } from "../Clock"

/* global jest, describe, it, expect, beforeAll, afterAll */

beforeAll(() => {
  jest.useFakeTimers()
  jest.setSystemTime(new Date("2024-01-01T12:30:45Z"))
})

afterAll(() => {
  jest.useRealTimers()
})

describe("Clock", () => {
  it("renders the current time in hours, minutes, and seconds", () => {
    render(<Clock />)

    // Check for hours:minutes format
    expect(screen.getByText("12:30")).toBeInTheDocument()

    // Check for seconds element by className
    const clockElement = document.querySelector(".secs")
    expect(clockElement).toBeInTheDocument()
    expect(clockElement).toHaveTextContent("45")
  })

  it("updates the time every second", () => {
    render(<Clock />)

    // Get initial seconds
    const secsElement = document.querySelector(".secs")
    expect(secsElement).toHaveTextContent("45")

    act(() => {
      jest.advanceTimersByTime(1000)
    })

    // Check seconds have updated
    expect(secsElement).toHaveTextContent("46")
  })
})

describe("TimeSinceLastImageClock", () => {
  const camera = {
    name: "cam1",
    title: "Camera 1",
    channels: [],
    location: "loc",
    time_since_clock: { label: "Since last image:" },
  }
  const baseMeta = {
    1: {
      "Date begin": "2024-01-01T00:00:00",
      "Exposure time": 10,
    },
  }

  it("renders null if no metadata row", () => {
    const { container } = render(
      <TimeSinceLastImageClock metadata={{}} camera={camera} />
    )
    expect(container.firstChild).toBeNull()
  })

  it("shows can't ascertain if required fields are missing", () => {
    render(
      <TimeSinceLastImageClock
        metadata={{ 1: { "Date begin": "2024-01-01T00:00:00" } }}
        camera={camera}
      />
    )
    expect(screen.getByText(/Can't ascertain/i)).toBeInTheDocument()
  })

  it("shows time elapsed since last image", () => {
    render(<TimeSinceLastImageClock metadata={baseMeta} camera={camera} />)
    expect(screen.getByText(/Since last image:/)).toBeInTheDocument()

    const timeElapsedElement = document.querySelector(".timeElapsed")
    expect(timeElapsedElement).toBeInTheDocument()
  })

  it("shows offline message when not online", () => {
    render(<TimeSinceLastImageClock metadata={baseMeta} camera={camera} />)

    act(() => {
      window.dispatchEvent(
        new CustomEvent("ws_status_change", { detail: { online: false } })
      )
    })

    expect(screen.getByText(/Lost comms with app/)).toBeInTheDocument()
  })

  it("updates metadata when camera event is received", () => {
    render(<TimeSinceLastImageClock metadata={baseMeta} camera={camera} />)

    const newMetadata = {
      2: {
        "Date begin": "2024-01-01T01:00:00",
        "Exposure time": 15,
      },
    }

    act(() => {
      window.dispatchEvent(
        new CustomEvent("camera", {
          detail: {
            data: newMetadata,
            dataType: "metadata",
          },
        })
      )
    })

    // Component should still render since it has valid metadata
    expect(screen.getByText(/Since last image:/)).toBeInTheDocument()
  })

  it("updates metadata when channel event is received", () => {
    render(<TimeSinceLastImageClock metadata={baseMeta} camera={camera} />)

    const latestMetadata = {
      3: {
        "Date begin": "2024-01-01T02:00:00",
        "Exposure time": 20,
      },
    }

    act(() => {
      window.dispatchEvent(
        new CustomEvent("channel", {
          detail: {
            data: latestMetadata,
            dataType: "latestMetadata",
          },
        })
      )
    })

    expect(screen.getByText(/Since last image:/)).toBeInTheDocument()
  })
})
