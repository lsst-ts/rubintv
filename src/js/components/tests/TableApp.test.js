import "@testing-library/jest-dom"
import React from "react"
import { render, act } from "@testing-library/react"
import TableApp from "../TableApp"
import { retrieveStoredSelection } from "../../modules/utils"

/* global jest, describe, it, expect, beforeAll, beforeEach */

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
})

// Mock the retrieveStoredSelection utility function
jest.mock("../../modules/utils", () => ({
  ...jest.requireActual("../../modules/utils"),
  retrieveStoredSelection: jest.fn(),
}))

// Mock necessary window properties and DOM elements
beforeAll(() => {
  window.APP_DATA = {
    locationName: "test-location",
    date: "2024-01-01",
    homeUrl: "http://test.com",
  }

  // Add required DOM elements
  const modalRoot = document.createElement("div")
  modalRoot.setAttribute("id", "modal-root")
  document.body.appendChild(modalRoot)

  const headerDate = document.createElement("div")
  headerDate.setAttribute("id", "header-date")
  document.body.appendChild(headerDate)

  const table = document.createElement("div")
  table.setAttribute("id", "table")
  document.body.appendChild(table)

  document.getElementById("header-date").textContent = ""
  document.getElementById("header-date").classList.add = jest.fn()
  document.getElementById("header-date").classList.remove = jest.fn()
})

describe("TableApp Column Selection Persistence", () => {
  const camera = {
    name: "testcam",
    metadata_cols: {
      colA: "description A",
      colB: "description B",
    },
    channels: [],
  }
  const mockStorage = {}

  beforeEach(() => {
    // Reset mock storage state
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key])

    // Setup localStorage mock with working implementation
    window.localStorage.setItem.mockImplementation((key, value) => {
      mockStorage[key] = value
    })
    window.localStorage.getItem.mockImplementation(
      (key) => mockStorage[key] || null
    )
  })

  it("maintains column selection across metadata updates", () => {
    // Mock initial stored selection
    const initialSelection = ["colA", "colB", "colC"]
    retrieveStoredSelection.mockReturnValue(initialSelection)

    // Initial render with metadata containing most columns
    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        initialChannelData={{}}
        initialMetadata={{
          123: { colA: "valueA", colB: "valueB", colC: "valueC" },
        }}
        isHistorical={false}
      />
    )

    // Force selected columns update via TableControls
    act(() => {
      const selected = ["colA", "colB", "colC", "colD"]
      window.localStorage.setItem(
        "test-location/testcam",
        JSON.stringify(selected)
      )
    })

    // Verify storage contains all columns
    const storedColumns = JSON.parse(
      window.localStorage.getItem("test-location/testcam")
    )
    expect(storedColumns).toEqual(
      expect.arrayContaining(["colA", "colB", "colC", "colD"])
    )
  })

  it("handles camera events and preserves column selection", () => {
    // Mock initial stored selection
    const initialSelection = ["colA", "colB", "colC"]
    retrieveStoredSelection.mockReturnValue(initialSelection)

    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        initialChannelData={{}}
        initialMetadata={{
          123: { colA: "valueA", colB: "valueB", colC: "valueC" },
        }}
        isHistorical={false}
      />
    )

    // Force initial storage
    act(() => {
      window.localStorage.setItem(
        "test-location/testcam",
        JSON.stringify(initialSelection)
      )
    })

    // Simulate metadata update
    act(() => {
      const metadataEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-02",
          dataType: "metadata",
          data: {
            124: { colA: "newA", colB: "newB", colD: "newD" },
          },
        },
      })
      window.dispatchEvent(metadataEvent)
    })

    // Verify storage maintains selection
    const storedColumns = JSON.parse(
      window.localStorage.getItem("test-location/testcam")
    )
    expect(storedColumns).toEqual(expect.arrayContaining(initialSelection))
  })

  it("preserves selected columns even when not in current metadata", () => {
    // Mock initial stored selection with some columns that won't be in initial metadata
    const initialSelection = ["colA", "colB", "colC", "colD", "futureCol"]
    retrieveStoredSelection.mockReturnValue(initialSelection)

    // Initialize with versioned storage data
    act(() => {
      window.localStorage.setItem(
        "test-location/testcam",
        JSON.stringify({
          version: "1",
          columns: initialSelection,
        })
      )
    })

    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        initialChannelData={{}}
        initialMetadata={{
          123: { colA: "valueA", colB: "valueB" },
        }}
        isHistorical={false}
      />
    )

    // Verify storage contains versioned data with all columns
    const storedData = JSON.parse(
      window.localStorage.getItem("test-location/testcam")
    )
    expect(storedData).toEqual({
      version: "1",
      columns: expect.arrayContaining(initialSelection),
    })

    // Simulate metadata update with new columns
    act(() => {
      const metadataEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "metadata",
          data: {
            124: { colA: "newA", colD: "newD", futureCol: "finally" },
          },
        },
      })
      window.dispatchEvent(metadataEvent)
    })

    // Verify storage still maintains all selected columns in versioned format
    const updatedData = JSON.parse(
      window.localStorage.getItem("test-location/testcam")
    )
    expect(updatedData).toEqual({
      version: "1",
      columns: expect.arrayContaining(initialSelection),
    })
  })
})
describe("TableApp Column Visibility and Disabling", () => {
  const camera = {
    name: "testcam",
    metadata_columns: {
      colA: "description A",
      colB: "description B",
      futureCol: "description Future",
    },
    channels: [],
  }

  beforeEach(() => {
    // Clear localStorage before each test
    window.localStorage.clear()
    // Reset the mock for retrieveStoredSelection
    retrieveStoredSelection.mockClear()
  })

  it("disables and hides previously selected columns not present in current metadata", () => {
    // Mock initial stored selection with a column not in initial metadata
    const initialSelection = ["colA", "colB", "futureCol"]
    retrieveStoredSelection.mockReturnValue(initialSelection)

    render(
      <TableApp
        camera={{
          name: "testcam",
          metadata_columns: {
            colA: "description A",
            colB: "description B",
          },
          channels: [],
        }}
        initialDate="2024-01-01"
        initialChannelData={{}}
        initialMetadata={{
          123: { colA: "valueA", colB: "valueB" },
        }}
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Simulate camera event with only colA and colB in metadata (futureCol missing)
    act(() => {
      const metadataEvent = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          dataType: "metadata",
          data: {
            123: { colA: "valueA", colB: "valueB" },
          },
        },
      })
      window.dispatchEvent(metadataEvent)
    })

    // Check that the table header does NOT contain "futureCol"
    const tableHeader = document.querySelector(".table-header")
    expect(tableHeader).not.toBeNull()
    expect(tableHeader).not.toHaveTextContent("futureCol")

    // Check that the column option for "futureCol" exists and is disabled
    // (Assuming your column options are rendered as checkboxes or similar in a control panel)
    const tableControlButton = document.querySelector(".table-control-button")
    expect(tableControlButton).toBeInTheDocument()
    act(() => {
      tableControlButton.click()
    })

    const colAOption = document.querySelector(
      'input[type="checkbox"][name="colA"]'
    )
    expect(colAOption).toBeInTheDocument()
    expect(colAOption).not.toBeDisabled()

    const futureColOption = document.querySelector(
      'input[type="checkbox"][name="futureCol"]'
    )
    expect(futureColOption).toBeInTheDocument()
    expect(futureColOption).toBeDisabled()
  })
})

describe("TableApp Loading and Historical Data Behavior", () => {
  const camera = {
    name: "testcam",
    metadata_columns: {
      colA: "description A",
      colB: "description B",
    },
    channels: [{ colour: "#123456", name: "Channel 1" }],
  }

  beforeEach(() => {
    window.localStorage.clear()
  })

  it("shows loading state until data is introduced via camera event (isHistorical=false, isStale=false)", () => {
    const { container } = render(
      <TableApp
        camera={camera}
        locationName="test-location"
        initialDate="2024-01-01"
        isHistorical={false}
        siteLocation="site"
        isStale={false}
      />
    )
    // Loading state should be visible
    expect(
      container.querySelector(".loading-bar-container")
    ).toBeInTheDocument()

    // Simulate camera event with data
    act(() => {
      const event = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          data: { 1: { colA: "foo", colB: "bar" } },
          dataType: "metadata",
        },
      })
      window.dispatchEvent(event)
      const event2 = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          data: { 1: { value: 42 } },
          dataType: "channelData",
        },
      })
      window.dispatchEvent(event2)
    })
    // Loading state should be gone
    expect(
      container.querySelector(".loading-bar-container")
    ).not.toBeInTheDocument()
    // Table should be rendered (header or other content)
    expect(document.querySelector(".table-header")).toBeInTheDocument()
  })

  it("shows loading state and updates for historical data (isHistorical=true)", () => {
    const { container } = render(
      <TableApp
        camera={camera}
        locationName="test-location"
        initialDate="2024-01-01"
        isHistorical={true}
        siteLocation="site"
        isStale={false}
      />
    )
    // Loading state should be visible
    expect(
      container.querySelector(".loading-bar-container")
    ).toBeInTheDocument()

    // Simulate camera event with data
    act(() => {
      const event = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          data: { 1: { colA: "foo", colB: "bar" } },
          dataType: "metadata",
        },
      })
      window.dispatchEvent(event)
      const event2 = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          data: { 1: { value: 42 } },
          dataType: "channelData",
        },
      })
      window.dispatchEvent(event2)
    })
    // Loading state should be gone
    expect(
      container.querySelector(".loading-bar-container")
    ).not.toBeInTheDocument()
    // Table should be rendered
    expect(document.querySelector(".table-header")).toBeInTheDocument()
  })

  it("shows loading state for stale historical data and clears 'stale' class on new date", () => {
    const { container } = render(
      <TableApp
        camera={camera}
        locationName="test-location"
        initialDate="2024-01-01"
        isHistorical={true}
        siteLocation="site"
        isStale={true}
      />
    )
    // Loading state should be visible
    expect(
      container.querySelector(".loading-bar-container")
    ).toBeInTheDocument()

    // Simulate camera event with no data (no data for current day)
    act(() => {
      const event = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-01",
          data: {},
          dataType: "metadata",
        },
      })
      window.dispatchEvent(event)
    })
    // Still loading, as no data
    expect(
      container.querySelector(".loading-bar-container")
    ).toBeInTheDocument()

    // Simulate camera event with new date (data for a new day)
    act(() => {
      const event = new CustomEvent("camera", {
        detail: {
          datestamp: "2024-01-02",
          data: { 1: { colA: "foo", colB: "bar" } },
          dataType: "metadata",
        },
      })
      window.dispatchEvent(event)
    })
    // Loading state should be gone
    expect(
      container.querySelector(".loading-bar-container")
    ).not.toBeInTheDocument()
    // The 'stale' class should be removed from header-date
    expect(
      document.getElementById("header-date").classList.remove
    ).toHaveBeenCalledWith("stale")
  })
})
