import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, act } from "@testing-library/react"
import PerDay from "../PerDay"
import { getImageAssetUrl } from "../../modules/utils"
import { homeUrl } from "../../config"

/* global jest, describe, it, expect, beforeEach, beforeAll */

// Mock external dependencies
jest.mock("../../modules/utils", () => ({
  getImageAssetUrl: jest.fn((path) => `http://mock.test/images/${path}`),
}))

jest.mock("../../config", () => ({
  homeUrl: "http://test.com/",
}))

describe("PerDay Component", () => {
  const mockCamera = {
    name: "testcam",
    channels: [
      {
        name: "channel1",
        label: "Channel 1 Label",
        title: "Channel 1 Title",
        icon: "icon1",
        colour: "#ff0000",
      },
      {
        name: "channel2",
        title: "Channel 2 Title",
        icon: "",
        colour: "#00ff00",
      },
    ],
    extra_buttons: [
      {
        name: "extra1",
        title: "Extra Button 1",
        linkURL: "http://external.com",
        logo: "logo1.png",
        text_colour: "#ffffff",
        text_shadow: true,
      },
    ],
    night_report_label: "Night Report",
  }

  const defaultProps = {
    locationName: "test-location",
    camera: mockCamera,
    initialDate: "2024-01-01",
    initialNRLink: "",
    isHistorical: false,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe("Initial Rendering", () => {
    it("renders without crashing", () => {
      render(<PerDay {...defaultProps} />)
      expect(document.body).toBeInTheDocument()
    })

    it("renders night report link when initialNRLink is provided", () => {
      render(<PerDay {...defaultProps} initialNRLink="current" />)

      expect(screen.getByText("Night's Evolution")).toBeInTheDocument()
      expect(screen.getByText("Night Report")).toBeInTheDocument()
      expect(screen.getByRole("link")).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/night_report"
      )
    })

    it("does not render night report link when initialNRLink is empty", () => {
      render(<PerDay {...defaultProps} initialNRLink="" />)

      expect(screen.queryByText("Night's Evolution")).not.toBeInTheDocument()
    })

    it("does not render per day channels initially when no perDay data", () => {
      render(<PerDay {...defaultProps} />)

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })
  })

  describe("Camera Event Handling", () => {
    it("handles perDay camera events and renders channels", () => {
      render(<PerDay {...defaultProps} />)

      const perDayData = {
        channel1: { filename: "test_file1.mp4" },
        channel2: { filename: "test_file2.mp4" },
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

      expect(screen.getByText("Per Day Channels")).toBeInTheDocument()
      expect(screen.getByText("Channel 1 Label")).toBeInTheDocument()
      expect(screen.getByText("Channel 2 Title")).toBeInTheDocument()

      // Check that buttons have correct links
      const channel1Link = screen.getByText("Channel 1 Label").closest("a")
      expect(channel1Link).toHaveAttribute(
        "href",
        "http://test.com/event_video/test-location/testcam/channel1/test_file1.mp4"
      )
    })

    it("handles nightReportLink camera events", () => {
      render(<PerDay {...defaultProps} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { nightReportLink: true },
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.getByText("Night's Evolution")).toBeInTheDocument()
      expect(screen.getByText("Night Report")).toBeInTheDocument()
    })

    it("updates date when datestamp changes", () => {
      render(<PerDay {...defaultProps} />)

      // First event with initial date
      act(() => {
        const cameraEvent1 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { channel1: { filename: "file1.mp4" } },
          },
        })
        window.dispatchEvent(cameraEvent1)
      })

      expect(screen.getByText("2024-01-01")).toBeInTheDocument()

      // Second event with new date
      act(() => {
        const cameraEvent2 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-02",
            dataType: "perDay",
            data: { channel1: { filename: "file2.mp4" } },
          },
        })
        window.dispatchEvent(cameraEvent2)
      })

      expect(screen.getByText("2024-01-02")).toBeInTheDocument()
    })

    it("clears perDay data when date changes", () => {
      render(<PerDay {...defaultProps} />)

      // First event with data
      act(() => {
        const cameraEvent1 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { channel1: { filename: "file1.mp4" } },
          },
        })
        window.dispatchEvent(cameraEvent1)
      })

      expect(screen.getByText("Per Day Channels")).toBeInTheDocument()

      // Second event with new date (should clear previous data)
      act(() => {
        const cameraEvent2 = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-02",
            dataType: "perDay",
            data: {},
          },
        })
        window.dispatchEvent(cameraEvent2)
      })

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })

    it("ignores non-perDay events", () => {
      render(<PerDay {...defaultProps} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "metadata",
            data: { some: "data" },
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })
  })

  describe("Button Component", () => {
    it("renders button with all props", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      const button = screen.getByText("Channel 1 Label").closest("a")
      expect(button).toHaveClass("button", "button-large", "channel1")
      expect(button).toHaveStyle("background-color: #ff0000")

      const img = button?.querySelector("img")
      expect(img).toHaveAttribute("src", "http://mock.test/images/icon1.svg")

      expect(screen.getByText("2024-01-01")).toBeInTheDocument()
    })

    it("uses channel name as icon when icon is empty", () => {
      const perDayData = {
        channel2: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      expect(getImageAssetUrl).toHaveBeenCalledWith("channel2.svg")
    })

    it("uses title when label is not provided", () => {
      const perDayData = {
        channel2: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      expect(screen.getByText("Channel 2 Title")).toBeInTheDocument()
    })
  })

  describe("Extra Buttons", () => {
    it("renders extra buttons for non-historical data", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} isHistorical={false} />)

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

      expect(screen.getByText("Extra Button 1")).toBeInTheDocument()

      const extraButton = screen.getByText("Extra Button 1").closest("a")
      expect(extraButton).toHaveClass("button-logo", "t-shadow")
      expect(extraButton).toHaveStyle("color: #ffffff")
      expect(extraButton).toHaveStyle(
        "background-image: url(http://mock.test/images/logos/logo1.png)"
      )
    })

    it("does not render extra buttons for historical data", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} isHistorical={true} />)

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

      expect(screen.queryByText("Extra Button 1")).not.toBeInTheDocument()
    })

    it("handles extra buttons without text styling", () => {
      const cameraWithoutStyling = {
        ...mockCamera,
        extra_buttons: [
          {
            name: "plain",
            title: "Plain Button",
            linkURL: "http://plain.com",
            logo: "plain.png",
          },
        ],
      }

      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(
        <PerDay
          {...defaultProps}
          camera={cameraWithoutStyling}
          isHistorical={false}
        />
      )

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

      const plainButton = screen.getByText("Plain Button").closest("a")
      expect(plainButton).not.toHaveClass("t-shadow")
      expect(plainButton).not.toHaveStyle("color: #ffffff")
    })
  })

  describe("NightReportLink Component", () => {
    it("renders night report link with date", () => {
      render(<PerDay {...defaultProps} initialNRLink="2024-01-01" />)

      expect(screen.getByText("Night's Evolution")).toBeInTheDocument()
      expect(
        screen.getByText("Night Report for 2024-01-01")
      ).toBeInTheDocument()

      const link = screen.getByRole("link")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/night_report/2024-01-01"
      )

      const img = link.querySelector("img")
      expect(img).toHaveAttribute(
        "src",
        "http://test.com/static/images/crescent-moon.svg"
      )
    })

    it("renders current night report link", () => {
      render(<PerDay {...defaultProps} initialNRLink="current" />)

      expect(screen.getByText("Night Report")).toBeInTheDocument()

      const link = screen.getByRole("link")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/night_report"
      )
    })

    it("does not render when nightReportLink is empty", () => {
      render(<PerDay {...defaultProps} initialNRLink="" />)

      expect(screen.queryByText("Night's Evolution")).not.toBeInTheDocument()
    })

    it("handles camera without night_report_label", () => {
      const cameraWithoutLabel = {
        ...mockCamera,
        night_report_label: undefined,
      }

      render(
        <PerDay
          {...defaultProps}
          camera={cameraWithoutLabel}
          initialNRLink="current"
        />
      )

      expect(screen.getByText("Night's Evolution")).toBeInTheDocument()
      // Should show empty string when no label
      const link = screen.getByRole("link")
      expect(link.textContent).not.toContain("Night Report")
    })
  })

  describe("Conditional Rendering", () => {
    it("does not render PerDayChannels when perDay is empty", () => {
      render(<PerDay {...defaultProps} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: {},
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })

    it("does not render PerDayChannels when perDay is null", () => {
      render(<PerDay {...defaultProps} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: null,
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })

    it("renders PerDayChannels when perDay has data", () => {
      render(<PerDay {...defaultProps} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            datestamp: "2024-01-01",
            dataType: "perDay",
            data: { channel1: { filename: "test.mp4" } },
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.getByText("Per Day Channels")).toBeInTheDocument()
    })
  })

  describe("Component Cleanup", () => {
    it("removes event listener on unmount", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(<PerDay {...defaultProps} />)

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

  describe("Edge Cases", () => {
    it("handles camera without extra_buttons", () => {
      const cameraWithoutExtras = {
        ...mockCamera,
        extra_buttons: undefined,
      }

      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} camera={cameraWithoutExtras} />)

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

      expect(screen.getByText("Per Day Channels")).toBeInTheDocument()
      expect(screen.queryByText("Extra Button 1")).not.toBeInTheDocument()
    })

    it("handles camera with empty channels array", () => {
      const cameraWithoutChannels = {
        ...mockCamera,
        channels: [],
      }

      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} camera={cameraWithoutChannels} />)

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

      expect(screen.queryByText("Per Day Channels")).not.toBeInTheDocument()
    })

    it("handles perDay data for non-existent channels", () => {
      const perDayData = {
        nonexistent: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      // Should render the section but no channel buttons
      expect(screen.getByText("Per Day Channels")).toBeInTheDocument()
      expect(screen.queryByText("Channel 1 Label")).not.toBeInTheDocument()
    })
  })

  describe("URL Construction", () => {
    it("constructs correct event video URLs", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      const link = screen.getByText("Channel 1 Label").closest("a")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/event_video/test-location/testcam/channel1/test_file.mp4"
      )
    })

    it("constructs correct external URLs for extra buttons", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      const extraButton = screen.getByText("Extra Button 1").closest("a")
      expect(extraButton).toHaveAttribute("href", "http://external.com/")
    })

    it("constructs correct night report URLs", () => {
      render(<PerDay {...defaultProps} initialNRLink="2024-01-01" />)

      const link = screen.getByRole("link")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/night_report/2024-01-01"
      )
    })
  })

  describe("Accessibility", () => {
    it("has proper navigation role", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} />)

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

      const nav = document.querySelector("nav")
      expect(nav).toHaveAttribute("role", "navigation")
      expect(nav).toHaveAttribute("id", "per-day-menu")
    })

    it("has proper heading structure", () => {
      const perDayData = {
        channel1: { filename: "test_file.mp4" },
      }

      render(<PerDay {...defaultProps} initialNRLink="current" />)

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

      const headings = screen.getAllByRole("heading", { level: 3 })
      expect(headings).toHaveLength(2)
      expect(headings[0]).toHaveTextContent("Per Day Channels")
      expect(headings[1]).toHaveTextContent("Night's Evolution")
    })
  })
})
