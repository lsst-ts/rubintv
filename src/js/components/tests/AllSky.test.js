import "@testing-library/jest-dom"
import React from "react"
import { render, screen, act, waitFor } from "@testing-library/react"
import AllSky from "../AllSky"
import { getHistoricalData } from "../../modules/utils"

/* global jest, describe, it, expect, beforeEach, beforeAll */

// Mock utility functions
jest.mock("../../modules/utils", () => ({
  getMediaProxyUrl: jest.fn(
    (mediaType, locationName, cameraName, channelName, filename) =>
      `http://proxy.test/${mediaType}/${locationName}/${cameraName}/${channelName}/${filename}`
  ),
  getHistoricalData: jest.fn(),
}))

// Mock RubinCalendar component
jest.mock("../RubinCalendar", () => ({
  __esModule: true,
  default: ({ selectedDate, camera, locationName }) => (
    <div data-testid="rubin-calendar">
      Mock Calendar - {selectedDate} - {camera.name} - {locationName}
    </div>
  ),
}))

beforeAll(() => {
  // Add required DOM elements
  const headerDate = document.createElement("div")
  headerDate.setAttribute("id", "header-date")
  document.body.appendChild(headerDate)
})

describe("AllSky Component", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [],
  }

  const mockCalendar = {
    "2024-01-01": { hasData: true },
    "2024-01-02": { hasData: false },
  }

  const mockStillEvent = {
    camera_name: "testcam",
    seq_num: 12345,
    filename: "test_still.jpg",
    ext: "jpg",
  }

  const mockMovieEvent = {
    camera_name: "testcam",
    seq_num: 67890,
    filename: "test_movie.mp4",
    ext: "mp4",
  }

  beforeEach(() => {
    jest.clearAllMocks()
    document.getElementById("header-date").textContent = ""
  })

  describe("Component Rendering", () => {
    it("renders current data mode correctly", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      expect(screen.getByText("2024-01-01")).toBeInTheDocument()
      expect(screen.queryByTestId("rubin-calendar")).not.toBeInTheDocument()
    })

    it("renders historical data mode correctly", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
          calendar={mockCalendar}
        />
      )

      expect(screen.getByText("2024-01-01")).toBeInTheDocument()
      expect(screen.getByTestId("rubin-calendar")).toBeInTheDocument()
      expect(
        screen.getByText("Mock Calendar - 2024-01-01 - testcam - test-location")
      ).toBeInTheDocument()
    })

    it("renders with calendar when provided", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
          calendar={mockCalendar}
        />
      )

      const calendar = screen.getByTestId("rubin-calendar")
      expect(calendar).toBeInTheDocument()
    })

    it("renders without calendar when not provided", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      const calendar = screen.getByTestId("rubin-calendar")
      expect(calendar).toHaveTextContent(
        "Mock Calendar - 2024-01-01 - testcam - test-location"
      )
    })
  })

  describe("Event Handling", () => {
    it("handles camera events with perDay data", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      const perDayData = {
        stills: mockStillEvent,
        movies: mockMovieEvent,
      }

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: perDayData,
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // Check that still is rendered
      expect(screen.getByText("Image 12345")).toBeInTheDocument()
      expect(screen.getByText("test_still.jpg")).toBeInTheDocument()

      // Check that movie is rendered
      expect(screen.getByText("67890")).toBeInTheDocument()
      expect(screen.getByText("test_movie.mp4")).toBeInTheDocument()
    })

    it("updates date when datestamp changes", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      expect(screen.getByText("2024-01-01")).toBeInTheDocument()

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-02",
            dataType: "perDay",
            data: { stills: mockStillEvent },
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // There should be two elements with the date: one in header-date and one in the component
      expect(screen.getAllByText("2024-01-02")).toHaveLength(2)
      expect(document.getElementById("header-date").textContent).toBe(
        "2024-01-02"
      )
    })

    it("ignores non-perDay events", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-02",
            dataType: "metadata",
            data: { some: "data" },
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // Date should not change
      expect(screen.getByText("2024-01-01")).toBeInTheDocument()
      expect(document.getElementById("header-date").textContent).toBe("")
    })

    it("merges new perDay data with existing data", () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      // First event with stills only
      act(() => {
        const cameraEvent1 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { stills: mockStillEvent },
          },
        })
        window.dispatchEvent(cameraEvent1)
      })

      expect(screen.getByText("Image 12345")).toBeInTheDocument()
      expect(screen.queryByText("67890")).not.toBeInTheDocument()

      // Second event with movies only
      act(() => {
        const cameraEvent2 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { movies: mockMovieEvent },
          },
        })
        window.dispatchEvent(cameraEvent2)
      })

      // Both should now be visible
      expect(screen.getByText("Image 12345")).toBeInTheDocument()
      expect(screen.getByText("67890")).toBeInTheDocument()
    })
  })

  describe("Historical Data Fetching", () => {
    it("fetches historical data when isHistorical is true", async () => {
      const mockHistoricalData = {
        perDay: {
          movies: mockMovieEvent,
          stills: mockStillEvent,
        },
      }

      getHistoricalData.mockResolvedValue(JSON.stringify(mockHistoricalData))

      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      await waitFor(() => {
        expect(getHistoricalData).toHaveBeenCalledWith(
          "test-location",
          "testcam",
          "2024-01-01"
        )
      })

      // Data should be rendered
      await waitFor(() => {
        // Only movies are in historical data
        expect(
          document.querySelector("allsky-current-image")
        ).not.toBeInTheDocument()
        expect(screen.getByText("67890")).toBeInTheDocument()
      })
    })

    it("handles historical data fetch failure", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      getHistoricalData.mockResolvedValue(null)

      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "No historical data found for",
          "test-location",
          "testcam",
          "2024-01-01"
        )
      })

      consoleSpy.mockRestore()
    })

    it("handles invalid historical data JSON", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      getHistoricalData.mockResolvedValue("invalid json")

      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      await waitFor(() => {
        expect(getHistoricalData).toHaveBeenCalled()
      })

      // Should not crash, error should be caught
      expect(screen.getByText("2024-01-01")).toBeInTheDocument()

      consoleSpy.mockRestore()
    })

    it("handles empty perDay data", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      const mockHistoricalData = { perDay: {} }

      getHistoricalData.mockResolvedValue(JSON.stringify(mockHistoricalData))

      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={true}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "No perDay data found for",
          "2024-01-01"
        )
      })

      consoleSpy.mockRestore()
    })

    it("does not fetch historical data when isHistorical is false", async () => {
      render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      // Wait a bit to ensure no async call is made
      await new Promise((resolve) => setTimeout(resolve, 100))

      expect(getHistoricalData).not.toHaveBeenCalled()
    })
  })

  describe("Component Cleanup", () => {
    it("removes event listeners on unmount", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(
        <AllSky
          initialDate="2024-01-01"
          isHistorical={false}
          locationName="test-location"
          camera={mockCamera}
        />
      )

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "camera",
        expect.any(Function)
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "camera",
        expect.any(Function)
      )

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })
  })
})

describe("AllSkyStill Component", () => {
  const mockStillEvent = {
    camera_name: "testcam",
    seq_num: 12345,
    filename: "test_still.jpg",
    ext: "jpg",
  }

  it("renders still image correctly", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { stills: mockStillEvent },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.getByText("Image 12345")).toBeInTheDocument()
    expect(screen.getByText("test_still.jpg")).toBeInTheDocument()

    const img = screen.getByRole("img")
    expect(img).toHaveAttribute(
      "src",
      "http://proxy.test/image/test-location/testcam/stills/test_still.jpg"
    )

    const link = img.closest("a")
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noreferrer")
    expect(link).toHaveAttribute(
      "href",
      "http://proxy.test/image/test-location/testcam/stills/test_still.jpg"
    )
  })

  it("does not render when still is null", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { stills: null },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.queryByText(/Image/)).not.toBeInTheDocument()
  })

  it("does not render when still is empty object", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { stills: {} },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.queryByText(/Image/)).not.toBeInTheDocument()
  })
})

describe("AllSkyMovie Component", () => {
  const mockMovieEvent = {
    camera_name: "testcam",
    seq_num: 67890,
    filename: "test_movie.mp4",
    ext: "mp4",
  }

  it("renders movie correctly", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { movies: mockMovieEvent },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.getByText("67890")).toBeInTheDocument()
    expect(screen.getByText("test_movie.mp4")).toBeInTheDocument()

    const video = document.querySelector("video")
    expect(video).toBeInTheDocument()
    expect(video).toHaveAttribute("controls")
    expect(video).toHaveAttribute("autoPlay")
    expect(video).toHaveAttribute("loop")
    expect(video).toHaveAttribute("width", "100%")

    const source = video.querySelector("source")
    expect(source).toHaveAttribute("type", "video/mp4")
    expect(source).toHaveAttribute(
      "src",
      "http://proxy.test/video/test-location/testcam/movies/test_movie.mp4"
    )
  })

  it("does not render when movie is null", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { movies: null },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.queryByText(/Images 1/)).not.toBeInTheDocument()
  })

  it("does not render when movie is empty object", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { movies: {} },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(screen.queryByText(/Images 1/)).not.toBeInTheDocument()
  })

  it("displays correct movie sequence range", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={{ name: "testcam", title: "Test Cam", channels: [] }}
      />
    )

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { movies: mockMovieEvent },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    const movieHeader = document.querySelector(".current-movie .subheader h3")
    // Check for the arrow and sequence range
    expect(movieHeader).toHaveTextContent("Images 1 → 67890")
  })
})

describe("Date Handling", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [],
  }

  beforeEach(() => {
    // Clear the header date before each test
    document.getElementById("header-date").textContent = ""
  })

  it("updates header date element when date changes via event", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={mockCamera}
      />
    )

    const headerDate = document.getElementById("header-date")
    expect(headerDate.textContent).toBe("")

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-03",
          dataType: "perDay",
          data: { stills: {} },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    expect(headerDate.textContent).toBe("2024-01-03")
  })

  it("does not update header date when datestamp matches current date", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={mockCamera}
      />
    )

    const headerDate = document.getElementById("header-date")
    expect(headerDate.textContent).toBe("")

    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: { stills: {} },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    // Header date should remain empty since datestamp matches current date
    expect(headerDate.textContent).toBe("")
  })
})

describe("Integration Tests", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [],
  }

  it("handles complete workflow for current data", () => {
    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        camera={mockCamera}
      />
    )

    // Initially no media content
    expect(screen.queryByRole("img")).not.toBeInTheDocument()
    expect(screen.queryByRole("video")).not.toBeInTheDocument()

    // Send perDay data event
    act(() => {
      const cameraEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "perDay",
          data: {
            stills: {
              camera_name: "testcam",
              seq_num: 100,
              filename: "still.jpg",
            },
            movies: {
              camera_name: "testcam",
              seq_num: 200,
              filename: "movie.mp4",
            },
          },
        },
      })
      window.dispatchEvent(cameraEvent)
    })

    // Both media types should now be rendered
    expect(screen.getByRole("img")).toBeInTheDocument()
    expect(screen.getByText("Image 100")).toBeInTheDocument()
    expect(screen.getByText("still.jpg")).toBeInTheDocument()

    const video = document.querySelector("video")
    expect(video).toBeInTheDocument()
    expect(screen.getByText("200")).toBeInTheDocument()
    expect(screen.getByText("movie.mp4")).toBeInTheDocument()
  })

  it("handles complete workflow for historical data", async () => {
    const mockHistoricalData = {
      perDay: {
        movies: {
          camera_name: "testcam",
          seq_num: 400,
          filename: "historical_movie.mp4",
        },
      },
    }

    getHistoricalData.mockResolvedValue(JSON.stringify(mockHistoricalData))

    render(
      <AllSky
        initialDate="2024-01-01"
        isHistorical={true}
        locationName="test-location"
        camera={mockCamera}
        calendar={{ "2024-01-01": { hasData: true } }}
      />
    )

    // Should show calendar
    expect(screen.getByTestId("rubin-calendar")).toBeInTheDocument()

    // Wait for historical data to load
    await waitFor(() => {
      expect(screen.getByText("400")).toBeInTheDocument()
      expect(screen.getByText("historical_movie.mp4")).toBeInTheDocument()
    })
  })
})
