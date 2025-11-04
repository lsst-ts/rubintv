/* global global*/
import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import AboveTableRow, { JumpButtons } from "../TableControls"
import { RubinTVTableContext } from "../contexts/contexts"
import { saveColumnSelection } from "../../modules/columnStorage"
import {
  _getById,
  findPrevNextDate,
  getCameraPageForDateUrl,
} from "../../modules/utils"

/* global jest, describe, it, expect, beforeEach, beforeAll, afterAll */

// Mock the column storage module
jest.mock("../../modules/columnStorage", () => ({
  saveColumnSelection: jest.fn(),
}))

// Mock the utils module
jest.mock("../../modules/utils", () => ({
  _getById: jest.fn((id) => {
    if (id === "table") {
      return { scrollIntoView: jest.fn() }
    }
    return null
  }),
  getImageAssetUrl: jest.fn(() => "mock-arrow.svg"),
  findPrevNextDate: jest.fn(() => ({ prevDate: null, nextDate: null })),
  getCameraPageForDateUrl: jest.fn(() => "mock-url"),
  unpackCalendarAsDateList: jest.fn(() => []),
}))

// Mock Clock components
jest.mock("../Clock", () => ({
  __esModule: true,
  default: () => <div data-testid="clock">Mock Clock</div>,
  TimeSinceLastImageClock: () => (
    <div data-testid="time-since-clock">Mock Time Since Clock</div>
  ),
}))

const mockContextValue = {
  siteLocation: "summit",
  locationName: "test-location",
  camera: { name: "testcam", channels: [], title: "Test Cam" },
  dayObs: "2024-01-01",
}

let defaultProps

describe("AboveTableRow Component", () => {
  const mockCamera = {
    name: "testcam",
    channels: [
      { name: "channel1", colour: "#ff0000" },
      { name: "channel2", colour: "#00ff00" },
    ],
    time_since_clock: { label: "Last Image" },
  }
  defaultProps = {
    locationName: "test-location",
    camera: mockCamera,
    availableColumns: ["colA", "colB", "colC"],
    selected: ["colA", "colB"],
    setSelected: jest.fn(),
    date: "2024-01-01",
    metadata: {},
    isHistorical: false,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders all components correctly for non-historical data", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} />
      </RubinTVTableContext.Provider>
    )

    expect(screen.getByText("2024-01-01")).toBeInTheDocument()
    expect(screen.getByText("Add/Remove Columns")).toBeInTheDocument()
    expect(screen.getByText("Download Metadata")).toBeInTheDocument()
    expect(screen.getByTestId("clock")).toBeInTheDocument()
    expect(screen.getByTestId("time-since-clock")).toBeInTheDocument()
  })

  it("does not render TimeSinceLastImageClock for historical data", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} isHistorical={true} />
      </RubinTVTableContext.Provider>
    )

    expect(screen.getByTestId("clock")).toBeInTheDocument()
    expect(screen.queryByTestId("time-since-clock")).not.toBeInTheDocument()
  })

  it("does not render TimeSinceLastImageClock when camera has no time_since_clock", () => {
    const cameraWithoutTimeClock = {
      ...mockCamera,
      time_since_clock: undefined,
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} camera={cameraWithoutTimeClock} />
      </RubinTVTableContext.Provider>
    )

    expect(screen.queryByTestId("time-since-clock")).not.toBeInTheDocument()
  })

  it("renders jump-to-date buttons when prev/next dates are available", () => {
    // Mock the utils functions to return prev/next dates
    findPrevNextDate.mockReturnValue({
      prevDate: "2024-01-01",
      nextDate: "2024-01-03",
    })

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} date="2024-01-02" />
      </RubinTVTableContext.Provider>
    )

    expect(
      screen.getByRole("button", { name: "Jump to previous date" })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Jump to next date" })
    ).toBeInTheDocument()
  })

  it("does not render jump buttons when no prev/next dates available", () => {
    findPrevNextDate.mockReturnValue({
      prevDate: null,
      nextDate: null,
    })

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} />
      </RubinTVTableContext.Provider>
    )

    expect(
      screen.queryByRole("button", { name: "Jump to previous date" })
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Jump to next date" })
    ).not.toBeInTheDocument()
  })

  it("navigates to correct URL when jump buttons are clicked", () => {
    findPrevNextDate.mockReturnValue({
      prevDate: "2024-01-01",
      nextDate: "2024-01-03",
    })
    getCameraPageForDateUrl.mockReturnValue("/test-url")

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow {...defaultProps} date="2024-01-02" />
      </RubinTVTableContext.Provider>
    )

    const prevButton = screen.getByRole("button", {
      name: "Jump to previous date",
    })
    fireEvent.click(prevButton)

    expect(getCameraPageForDateUrl).toHaveBeenCalledWith(
      "test-location",
      "testcam",
      "2024-01-01"
    )

    // Test next button as well
    const nextButton = screen.getByRole("button", {
      name: "Jump to next date",
    })
    fireEvent.click(nextButton)

    expect(getCameraPageForDateUrl).toHaveBeenCalledWith(
      "test-location",
      "testcam",
      "2024-01-03"
    )
  })
})

describe("TableControls Component", () => {
  const defaultProps = {
    cameraName: "testcam",
    availableColumns: ["colA", "colB", "colC", "colD"],
    selected: ["colA", "colB"],
    setSelected: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    // Mock window click events
    window.addEventListener = jest.fn()
    window.removeEventListener = jest.fn()
  })

  it("renders the control button correctly", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute("aria-expanded", "false")
    expect(button).toHaveAttribute("aria-controls", "table-controls")
    expect(button).toHaveAttribute("aria-haspopup", "true")
  })

  it("opens and closes the controls panel when button is clicked", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })

    // Initially closed
    expect(button).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByText("colA")).not.toBeInTheDocument()

    // Open panel
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("colA")).toBeInTheDocument()

    // Close panel
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByText("colA")).not.toBeInTheDocument()
  })

  it("displays checkboxes for all columns (available and selected unavailable)", () => {
    const propsWithUnavailable = {
      ...defaultProps,
      selected: ["colA", "colB", "unavailableCol"],
      availableColumns: ["colA", "colB", "colC"],
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...propsWithUnavailable}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    // Available columns should be enabled
    expect(screen.getByRole("checkbox", { name: "colA" })).not.toBeDisabled()
    expect(screen.getByRole("checkbox", { name: "colB" })).not.toBeDisabled()
    expect(screen.getByRole("checkbox", { name: "colC" })).not.toBeDisabled()

    // Unavailable selected column should be disabled
    expect(
      screen.getByRole("checkbox", { name: "unavailableCol" })
    ).toBeDisabled()
  })

  it("handles checkbox selection correctly", () => {
    const mockSetSelected = jest.fn()

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          setSelected={mockSetSelected}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    // Select a new column
    const colCCheckbox = screen.getByRole("checkbox", { name: "colC" })
    fireEvent.click(colCCheckbox)

    expect(saveColumnSelection).toHaveBeenCalledWith(
      ["colA", "colB", "colC"],
      "test-location",
      "testcam"
    )
    expect(mockSetSelected).toHaveBeenCalledWith(["colA", "colB", "colC"])
  })

  it("handles deselecting columns correctly", () => {
    const mockSetSelected = jest.fn()

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          setSelected={mockSetSelected}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    // Deselect an existing column
    const colACheckbox = screen.getByRole("checkbox", { name: "colA" })
    fireEvent.click(colACheckbox)

    expect(saveColumnSelection).toHaveBeenCalledWith(
      ["colB"],
      "test-location",
      "testcam"
    )
    expect(mockSetSelected).toHaveBeenCalledWith(["colB"])
  })

  it("prevents deselecting all columns", () => {
    const mockSetSelected = jest.fn()
    const propsWithOneSelected = {
      ...defaultProps,
      selected: ["colA"],
      setSelected: mockSetSelected,
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...propsWithOneSelected}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    // Try to deselect the last column
    const colACheckbox = screen.getByRole("checkbox", { name: "colA" })
    fireEvent.click(colACheckbox)

    // Should not call setSelected or saveColumnSelection
    expect(mockSetSelected).not.toHaveBeenCalled()
    expect(saveColumnSelection).not.toHaveBeenCalled()
  })

  it("closes panel when Escape key is pressed", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })

    // Open panel
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")

    // Press Escape on button
    fireEvent.keyDown(button, { key: "Escape" })
    expect(button).toHaveAttribute("aria-expanded", "false")
  })

  it("closes panel when Escape key is pressed on checkbox", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })

    // Open panel
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")

    // Press Escape on checkbox
    const checkbox = screen.getByRole("checkbox", { name: "colA" })
    fireEvent.keyDown(checkbox, { key: "Escape" })
    expect(button).toHaveAttribute("aria-expanded", "false")
  })

  it("closes panel when clicked outside", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )
    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("colA")).toBeInTheDocument()
    // Click outside the panel
    fireEvent.click(document.body)
    expect(button).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByText("colA")).not.toBeInTheDocument()
  })

  it("doesn't close panel when clicking inside", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )
    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("colA")).toBeInTheDocument()
    // Click inside the panel
    const checkbox = screen.getByRole("checkbox", { name: "colA" })
    fireEvent.click(checkbox)
    const optionsContainer = document.querySelector(".table-options")
    fireEvent.click(optionsContainer)
    expect(optionsContainer).toBeInTheDocument()
    expect(button).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("colA")).toBeInTheDocument()
  })

  it("uses correct grid columns based on number of available columns", () => {
    // Test with <= 45 columns (should use 2 columns)
    const { rerender } = render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...defaultProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    let optionsContainer = document.querySelector(".table-options")
    expect(optionsContainer).toHaveStyle("column-count: 2")

    // Test with > 45 columns (should use 3 columns)
    const manyColumns = Array.from({ length: 50 }, (_, i) => `col${i}`)
    const propsWithManyColumns = {
      ...defaultProps,
      availableColumns: manyColumns,
    }

    rerender(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...propsWithManyColumns}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    optionsContainer = document.querySelector(".table-options")
    expect(optionsContainer).toHaveStyle("column-count: 3")
  })

  it("displays columns in alphabetical order regardless of case", () => {
    const unsortedProps = {
      ...defaultProps,
      availableColumns: ["zebra", "alpha", "Beta"],
      selected: ["zebra"],
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...unsortedProps}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    const checkboxes = screen.getAllByRole("checkbox")
    const labels = checkboxes.map((checkbox) => checkbox.getAttribute("name"))

    expect(labels).toEqual(["alpha", "Beta", "zebra"])
  })
})

describe("JumpButtons Component", () => {
  const mockTable = {
    scrollIntoView: jest.fn(),
  }

  beforeAll(() => {
    _getById.mockReturnValue(mockTable)
  })

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders both jump buttons", () => {
    render(<JumpButtons />)

    const buttons = screen.getAllByRole("button")
    expect(buttons).toHaveLength(2)

    const topButton = screen.getByTitle("to top")
    const bottomButton = screen.getByTitle("to bottom")

    expect(topButton).toBeInTheDocument()
    expect(bottomButton).toBeInTheDocument()
  })

  it("scrolls to top when top button is clicked", () => {
    render(<JumpButtons />)

    const topButton = screen.getByTitle("to top")
    fireEvent.click(topButton)

    expect(mockTable.scrollIntoView).toHaveBeenCalledWith()
  })

  it("scrolls to bottom when bottom button is clicked", () => {
    render(<JumpButtons />)

    const bottomButton = screen.getByTitle("to bottom")
    fireEvent.click(bottomButton)

    expect(mockTable.scrollIntoView).toHaveBeenCalledWith(false)
  })

  it("displays arrow images", () => {
    render(<JumpButtons />)

    const images = screen.getAllByRole("img")
    expect(images).toHaveLength(2)

    images.forEach((img) => {
      expect(img).toHaveAttribute("src", "mock-arrow.svg")
    })
  })
})

describe("DownloadMetadataButton Component", () => {
  const mockCreateElement = jest.fn()
  const mockClick = jest.fn()
  const mockCreateObjectURL = jest.fn(() => "mock-url")
  const mockRevokeObjectURL = jest.fn()
  let originalCreateElement

  beforeAll(() => {
    originalCreateElement = document.createElement.bind(document)

    // Mock document.createElement
    mockCreateElement.mockImplementation((tagName) => {
      if (tagName === "a") {
        return {
          href: "",
          download: "",
          click: mockClick,
        }
      }
      return originalCreateElement(tagName)
    })
    document.createElement = mockCreateElement

    // Mock URL methods
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL

    // Mock Blob
    global.Blob = jest.fn().mockImplementation((content) => ({ content }))
  })

  afterAll(() => {
    document.createElement = originalCreateElement
  })

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders download button", () => {
    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          camera={{ name: "testcam", channels: [] }}
          availableColumns={[]}
          selected={[]}
          setSelected={jest.fn()}
          date="2024-01-01"
          metadata={{ 123: { col1: "value1" } }}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const downloadButton = screen.getByRole("button", {
      name: /download metadata/i,
    })
    expect(downloadButton).toBeInTheDocument()
  })

  it("downloads metadata when clicked", () => {
    const metadata = { 123: { col1: "value1", col2: "value2" } }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          camera={{ name: "testcam", channels: [] }}
          availableColumns={[]}
          selected={[]}
          setSelected={jest.fn()}
          date="2024-01-01"
          metadata={metadata}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const downloadButton = screen.getByRole("button", {
      name: /download metadata/i,
    })
    fireEvent.click(downloadButton)

    expect(global.Blob).toHaveBeenCalledWith([JSON.stringify(metadata)])
    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockClick).toHaveBeenCalled()
    expect(mockRevokeObjectURL).toHaveBeenCalledWith("mock-url")
  })

  it("uses correct filename format", () => {
    const metadata = { 123: { col1: "value1" } }
    let capturedDownload = ""

    mockCreateElement.mockImplementation((tagName) => {
      if (tagName === "a") {
        return {
          href: "",
          get download() {
            return capturedDownload
          },
          set download(value) {
            capturedDownload = value
          },
          click: mockClick,
        }
      }
      return originalCreateElement(tagName)
    })

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          camera={{ name: "testcam", channels: [] }}
          availableColumns={[]}
          selected={[]}
          setSelected={jest.fn()}
          date="2024-01-01"
          metadata={metadata}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const downloadButton = screen.getByRole("button", {
      name: /download metadata/i,
    })
    fireEvent.click(downloadButton)

    expect(capturedDownload).toBe("testcam_2024-01-01.json")
  })
})

describe("TableControls Integration", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("handles non-array selected values gracefully", () => {
    const mockSetSelected = jest.fn()
    // Simulate somehow getting a non-array value for selected
    const propsWithInvalidSelected = {
      ...defaultProps,
      selected: null, // Invalid value
      setSelected: mockSetSelected,
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...propsWithInvalidSelected}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    // Should still be able to select a column
    const colACheckbox = screen.getByRole("checkbox", { name: "colA" })
    fireEvent.click(colACheckbox)

    expect(mockSetSelected).toHaveBeenCalledWith(["colA"])
  })

  it("properly marks unavailable columns with correct styling", () => {
    const propsWithUnavailable = {
      ...defaultProps,
      selected: ["colA", "unavailableCol"],
      availableColumns: ["colA", "colB"],
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <AboveTableRow
          {...propsWithUnavailable}
          camera={{ name: "testcam", channels: [] }}
          date="2024-01-01"
          metadata={{}}
          isHistorical={false}
        />
      </RubinTVTableContext.Provider>
    )

    const button = screen.getByRole("button", { name: /add\/remove columns/i })
    fireEvent.click(button)

    const unavailableOption = screen
      .getByRole("checkbox", { name: "unavailableCol" })
      .closest(".table-option")
    expect(unavailableOption).toHaveClass("unavailable")

    const availableOption = screen
      .getByRole("checkbox", { name: "colA" })
      .closest(".table-option")
    expect(availableOption).not.toHaveClass("unavailable")
  })
})
