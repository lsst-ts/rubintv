import React from "react"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom"
import NightReport from "../NightReport"

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
})

// Mock data
const mockCamera = {
  name: "test-camera",
  night_report_label: "Test Camera Night Report",
}

const mockNightReport = {
  text: {
    text_efficiency_1: "Efficiency report line 1\nLine 2 with  double spaces",
    text_efficiency_2: "Another efficiency report",
    qa_link_1: "http://example.com/qa1",
    qa_link_2: "http://example.com/qa2",
  },
  plots: [
    {
      filename: "plot1.png",
      group: "Sky Quality",
      hash: "hash1",
    },
    {
      filename: "plot2.png",
      group: "Sky Quality",
      hash: "hash2",
    },
    {
      filename: "plot3.png",
      group: "Weather",
      hash: "hash3",
    },
  ],
}

const mockEmptyNightReport = {}

const defaultProps = {
  initialNightReport: mockNightReport,
  initialDate: "2023-12-01",
  camera: mockCamera,
  locationName: "test-location",
  homeUrl: "http://localhost/",
}

describe("NightReport", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  afterEach(() => {
    // Clean up event listeners
    document.body.innerHTML = ""
  })

  describe("Basic rendering", () => {
    it("renders night report with title and date", () => {
      render(<NightReport {...defaultProps} />)

      expect(
        screen.getByText("Test Camera Night Report for: 2023-12-01")
      ).toBeInTheDocument()
    })

    it("renders empty state when no night report data", () => {
      render(
        <NightReport
          {...defaultProps}
          initialNightReport={mockEmptyNightReport}
        />
      )

      expect(
        screen.getByText("There is no night report for today yet")
      ).toBeInTheDocument()
    })

    it("renders tabs for efficiency, qa plots, and plot groups", () => {
      render(<NightReport {...defaultProps} />)

      expect(screen.getByText("Efficiency")).toBeInTheDocument()
      expect(screen.getByText("QA Plots")).toBeInTheDocument()
      expect(screen.getByText("Sky Quality")).toBeInTheDocument()
      expect(screen.getByText("Weather")).toBeInTheDocument()
    })
  })

  describe("Tab functionality", () => {
    it("selects first tab by default when no localStorage value", () => {
      render(<NightReport {...defaultProps} />)

      const efficiencyTab = screen.getByText("Efficiency")
      expect(efficiencyTab).toHaveClass("selected")
    })

    it("uses localStorage value for initial selection", () => {
      localStorageMock.getItem.mockReturnValue("qa_plots")
      render(<NightReport {...defaultProps} />)

      const qaTab = screen.getByText("QA Plots")
      expect(qaTab).toHaveClass("selected")
    })

    it("switches tabs on click and updates localStorage", () => {
      render(<NightReport {...defaultProps} />)

      const weatherTab = screen.getByText("Weather")
      fireEvent.click(weatherTab)

      expect(weatherTab).toHaveClass("selected")
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "night-report-selected",
        "weather"
      )
    })

    it("does not update localStorage when clicking already selected tab", () => {
      render(<NightReport {...defaultProps} />)

      jest.clearAllMocks() // Clear previous calls

      const efficiencyTab = screen.getByText("Efficiency")
      fireEvent.click(efficiencyTab)

      expect(localStorageMock.setItem).not.toHaveBeenCalled()
    })
  })

  describe("Hidden tabs and keyboard shortcuts", () => {
    it("hides elana tab by default", () => {
      const nightReportWithElana = {
        ...mockNightReport,
        plots: [
          ...mockNightReport.plots,
          { filename: "elana.png", group: "elana", hash: "elana-hash" },
        ],
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={nightReportWithElana}
        />
      )

      const elanaTab = screen.getByText("elana")
      expect(elanaTab).toHaveClass("disabled")
    })

    it("reveals hidden tab when correct key sequence is typed", async () => {
      const nightReportWithElana = {
        ...mockNightReport,
        plots: [
          ...mockNightReport.plots,
          { filename: "elana.png", group: "elana", hash: "elana-hash" },
        ],
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={nightReportWithElana}
        />
      )

      const elanaTab = screen.getByText("elana")
      expect(elanaTab).toHaveClass("disabled")

      // Type the key sequence
      fireEvent.keyDown(document.body, { key: "e" })
      fireEvent.keyDown(document.body, { key: "l" })
      fireEvent.keyDown(document.body, { key: "a" })
      fireEvent.keyDown(document.body, { key: "n" })
      fireEvent.keyDown(document.body, { key: "a" })

      await waitFor(() => {
        expect(elanaTab).not.toHaveClass("disabled")
        expect(elanaTab).toHaveClass("selected")
      })
    })

    it("resets typed sequence when wrong key is pressed", () => {
      const nightReportWithElana = {
        ...mockNightReport,
        plots: [
          ...mockNightReport.plots,
          { filename: "elana.png", group: "elana", hash: "elana-hash" },
        ],
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={nightReportWithElana}
        />
      )
      fireEvent.keyDown(document.body, { key: "e" })
      fireEvent.keyDown(document.body, { key: "x" }) // Wrong key
      fireEvent.keyDown(document.body, { key: "l" })

      // Should not reveal any hidden tabs
      const tabs = document.getElementsByClassName("disabled")
      expect(tabs.length).toBeGreaterThan(0)
    })
  })

  describe("Text content rendering", () => {
    it("renders efficiency text content", () => {
      render(<NightReport {...defaultProps} />)

      expect(screen.getByText(/Efficiency report line 1/)).toBeInTheDocument()
      expect(screen.getByText(/Another efficiency report/)).toBeInTheDocument()
    })

    it("renders QA plots as links", () => {
      render(<NightReport {...defaultProps} />)

      fireEvent.click(screen.getByText("QA Plots"))

      const qaLink1 = screen.getByRole("link", { name: "qa_link_1" })
      const qaLink2 = screen.getByRole("link", { name: "qa_link_2" })

      expect(qaLink1).toHaveAttribute("href", "http://example.com/qa1")
      expect(qaLink2).toHaveAttribute("href", "http://example.com/qa2")
      expect(qaLink1).toHaveAttribute("target", "_blank")
    })

    it("handles multiline text with double spaces", () => {
      render(<NightReport {...defaultProps} />)

      const textElement = screen.getByText(/Line 2 with.*double spaces/)
      expect(textElement.innerHTML).toContain("&nbsp;&nbsp;") // Check for double spaces
    })
  })

  describe("Plot rendering", () => {
    it("renders plot images with correct URLs", () => {
      render(<NightReport {...defaultProps} />)

      fireEvent.click(screen.getByText("Sky Quality"))

      const plot1 = screen.getByAltText("plot1.png")
      const plot2 = screen.getByAltText("plot2.png")

      expect(plot1).toHaveAttribute(
        "src",
        "http://localhost/plot_image/test-location/test-camera/Sky Quality/plot1.png"
      )
      expect(plot2).toHaveAttribute(
        "src",
        "http://localhost/plot_image/test-location/test-camera/Sky Quality/plot2.png"
      )
    })

    it("renders plot captions", () => {
      render(<NightReport {...defaultProps} />)

      fireEvent.click(screen.getByText("Sky Quality"))

      expect(screen.getByText("plot1.png")).toBeInTheDocument()
      expect(screen.getByText("plot2.png")).toBeInTheDocument()
    })

    it("wraps plot images in links", () => {
      render(<NightReport {...defaultProps} />)

      fireEvent.click(screen.getByText("Sky Quality"))

      const plot1Link = screen.getByAltText("plot1.png").closest("a")
      expect(plot1Link).toHaveAttribute(
        "href",
        "http://localhost/plot_image/test-location/test-camera/Sky Quality/plot1.png"
      )
    })
  })

  describe("Event handling", () => {
    it("handles nightreport custom event with new data", async () => {
      render(<NightReport {...defaultProps} />)

      const newNightReport = {
        text: { text_new: "New efficiency report" },
        plots: [
          { filename: "new-plot.png", group: "New Group", hash: "new-hash" },
        ],
      }

      const event = new CustomEvent("nightreport", {
        detail: {
          datestamp: "2023-12-02",
          data: newNightReport,
          dataType: "nightReport",
        },
      })

      window.dispatchEvent(event)

      await waitFor(() => {
        expect(
          screen.getByText("Test Camera Night Report for: 2023-12-01")
        ).toBeInTheDocument()
        expect(screen.getByText("New Group")).toBeInTheDocument()
      })
    })

    it("ignores nightreport event with different dataType", () => {
      render(<NightReport {...defaultProps} />)

      const event = new CustomEvent("nightreport", {
        detail: {
          datestamp: "2023-12-02",
          data: { some: "data" },
          dataType: "otherType",
        },
      })

      window.dispatchEvent(event)

      // Should still show original content
      expect(screen.getByText("Efficiency")).toBeInTheDocument()
    })
  })

  describe("Edge cases", () => {
    it("handles night report with only text data", () => {
      const textOnlyReport = {
        text: { text_efficiency: "Only text data" },
      }

      render(
        <NightReport {...defaultProps} initialNightReport={textOnlyReport} />
      )

      expect(screen.getByText("Efficiency")).toBeInTheDocument()
      expect(screen.queryByText("Sky Quality")).not.toBeInTheDocument()
    })

    it("handles night report with only plot data", () => {
      const plotOnlyReport = {
        plots: [{ filename: "plot.png", group: "Test Group", hash: "hash" }],
      }

      render(
        <NightReport {...defaultProps} initialNightReport={plotOnlyReport} />
      )

      expect(screen.getByText("Test Group")).toBeInTheDocument()
      expect(screen.queryByText("Efficiency")).not.toBeInTheDocument()
    })

    it("handles empty text values", () => {
      const reportWithEmptyText = {
        text: {
          text_efficiency: "",
          text_valid: "Valid text",
          qa_empty: "",
        },
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={reportWithEmptyText}
        />
      )

      expect(screen.getByText("Valid text")).toBeInTheDocument()
    })

    it("sanitizes group names for tab IDs", () => {
      const reportWithSpecialChars = {
        plots: [
          {
            filename: "plot.png",
            group: "Group With Spaces & Special!",
            hash: "hash",
          },
        ],
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={reportWithSpecialChars}
        />
      )

      const tab = screen.getByText("Group With Spaces & Special!")
      expect(tab.getAttribute("id")).toMatch(/tabtitle-/)
    })
  })

  describe("Component cleanup", () => {
    it("removes event listeners on unmount", () => {
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")
      const { unmount } = render(<NightReport {...defaultProps} />)

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "nightreport",
        expect.any(Function)
      )
    })

    it("removes keyboard event listeners when all hidden tabs are revealed", async () => {
      const removeEventListenerSpy = jest.spyOn(
        document.body,
        "removeEventListener"
      )

      const nightReportWithElana = {
        ...mockNightReport,
        plots: [
          ...mockNightReport.plots,
          { filename: "elana.png", group: "elana", hash: "elana-hash" },
        ],
      }

      render(
        <NightReport
          {...defaultProps}
          initialNightReport={nightReportWithElana}
        />
      )

      // Reveal the hidden tab
      fireEvent.keyDown(document.body, { key: "e" })
      fireEvent.keyDown(document.body, { key: "l" })
      fireEvent.keyDown(document.body, { key: "a" })
      fireEvent.keyDown(document.body, { key: "n" })
      fireEvent.keyDown(document.body, { key: "a" })

      await waitFor(() => {
        expect(removeEventListenerSpy).toHaveBeenCalledWith(
          "keydown",
          expect.any(Function)
        )
      })
    })
  })
})
