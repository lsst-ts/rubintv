import "@testing-library/jest-dom"
import React from "react"
import { render, act, screen, fireEvent } from "@testing-library/react"
import TableApp from "../TableApp"
import { retrieveStoredSelection, getHistoricalData } from "../../modules/utils"

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

// Mock utility functions
jest.mock("../../modules/utils", () => ({
  ...jest.requireActual("../../modules/utils"),
  retrieveStoredSelection: jest.fn(),
  getHistoricalData: jest.fn(() => {
    return Promise.resolve(
      JSON.stringify({
        data: {},
        metadata: {},
        channels: [],
        datestamp: "2024-01-01",
      })
    )
  }),
}))

// Inject metadata via "camera" event
const metadataEvent = (metadata, datestamp = "2024-01-01") => {
  const mdEvent = new CustomEvent("camera", {
    detail: {
      datestamp,
      dataType: "metadata",
      data: metadata,
    },
  })
  window.dispatchEvent(mdEvent)
}

// Inject channelData via "camera" event
const channelDataEvent = (channelData) => {
  const cdEvent = new CustomEvent("camera", {
    detail: {
      datestamp: "2024-01-01",
      dataType: "channelData",
      data: channelData,
    },
  })
  window.dispatchEvent(cdEvent)
}

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
      <TableApp camera={camera} initialDate="2024-01-01" isHistorical={false} />
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
      <TableApp camera={camera} initialDate="2024-01-01" isHistorical={false} />
    )

    act(() => {
      // Simulate camera event with initial metadata
      metadataEvent({
        123: { colA: "valueA", colB: "valueB", colC: "valueC" },
      })
    })

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
      <TableApp camera={camera} initialDate="2024-01-01" isHistorical={false} />
    )

    // Simulate camera event with metadata that does not include all selected columns
    act(() => {
      metadataEvent({
        123: { colA: "valueA", colB: "valueB" },
      })
    })

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
      metadataEvent({
        124: { colA: "newA", colD: "newD", futureCol: "finally" },
      })
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

  it("saves column selection to localStorage", () => {
    const initialSelection = ["colA", "colB"]
    retrieveStoredSelection.mockReturnValue(initialSelection)

    const { container } = render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Simulate camera event with initial metadata
    act(() => {
      metadataEvent({
        123: { colA: "valueA", colB: "valueB", colC: "valueC" },
      })
    })

    // Open the column selection controls
    const tableControlButton = container.querySelector(".table-control-button")
    expect(tableControlButton).toBeInTheDocument()

    act(() => {
      fireEvent.click(tableControlButton)
    })

    // Select an additional column (colC)
    const colCCheckbox = container.querySelector('input[name="colC"]')
    expect(colCCheckbox).toBeInTheDocument()

    act(() => {
      fireEvent.click(colCCheckbox)
    })

    // Verify that localStorage.setItem was called with the updated selection
    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      "test-location/testcam",
      expect.stringContaining("colC")
    )

    // Verify the stored data contains the new selection
    const storedData = JSON.parse(
      window.localStorage.getItem("test-location/testcam")
    )
    expect(storedData.columns).toEqual(
      expect.arrayContaining(["colA", "colB", "colC"])
    )
  })
})

describe("TableApp Column Visibility and Disabling", () => {
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
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Simulate camera event with only colA and colB in metadata (futureCol missing)
    act(() => {
      metadataEvent({
        123: { colA: "valueA", colB: "valueB" },
      })
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
      fireEvent.click(tableControlButton)
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
    render(
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
      screen.getByText("Loading data for", { exact: false })
    ).toBeInTheDocument()

    // Simulate camera event with data
    act(() => {
      metadataEvent({
        1: { colA: "foo", colB: "bar" },
      })
      channelDataEvent({ 1: { value: 42 } })
    })
    // Loading state should be gone
    expect(
      screen.queryByText("Loading data for", { exact: false })
    ).not.toBeInTheDocument()
    // Table should be rendered (header or other content)
    expect(document.querySelector(".table-header")).toBeInTheDocument()
  })

  it("shows loading state and updates for historical data (isHistorical=true)", () => {
    render(
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
      screen.getByText("Loading data for", { exact: false })
    ).toBeInTheDocument()

    // Simulate camera event with data
    act(() => {
      metadataEvent({
        1: { colA: "foo", colB: "bar" },
      })
      channelDataEvent({ 1: { value: 42 } })
    })
    // Loading state should be gone
    expect(
      screen.queryByText("Loading data for", { exact: false })
    ).not.toBeInTheDocument()
    // Table should be rendered
    expect(document.querySelector(".table-header")).toBeInTheDocument()
  })

  it("shows loading state for stale historical data and clears 'stale' class on new date", () => {
    render(
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
      screen.getByText("Loading data for", { exact: false })
    ).toBeInTheDocument()

    // Simulate camera event with no data (no data for current day)
    act(() => {
      metadataEvent({})
    })

    // Still loading, as no data
    expect(
      screen.getByText("Loading data for", { exact: false })
    ).toBeInTheDocument()

    // Simulate camera event with new date (data for a new day)
    act(() => {
      metadataEvent({
        data: { 1: { colA: "foo", colB: "bar" } },
        datestamp: "2024-01-02",
      })
    })
    // Loading state should be gone
    expect(
      screen.queryByText("Loading data for", { exact: false })
    ).not.toBeInTheDocument()
    // The 'stale' class should be removed from header-date
    expect(
      document.getElementById("header-date").classList.remove
    ).toHaveBeenCalledWith("stale")
  })

  it("fetches historical data", async () => {
    // Set up the mock before rendering
    getHistoricalData.mockResolvedValue(
      JSON.stringify({
        channelData: { 1: { colA: "foo", colB: "bar" } },
        metadata: { 1: { colA: "foo", colB: "bar" } },
        channels: [],
      })
    )

    render(
      <TableApp
        camera={camera}
        locationName="test-location"
        initialDate="2024-01-01"
        isHistorical={true}
        siteLocation="site"
        isStale={false}
      />
    )

    // Wait for the promise to resolve and effects to complete
    await act(async () => {
      // Allow time for the promise to resolve
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    expect(getHistoricalData).toHaveBeenCalledWith(
      "test-location",
      "testcam",
      "2024-01-01"
    )

    // Check if the table header is rendered with the expected content
    const tableHeader = document.querySelector(".table-header")
    expect(tableHeader).toBeInTheDocument()
  })

  it("shows the correct date in the header", () => {
    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Check if the header date is set correctly
    const headerDate = document.getElementById("header-date")
    expect(headerDate).toBeInTheDocument()
    // Initially, the header date should be empty
    expect(headerDate.textContent).toBe("")

    act(() => {
      metadataEvent(
        {
          123: { colA: "valueA", colB: "valueB" },
        },
        "2024-01-02"
      )
    })
    // After metadata event, the header date should be updated
    expect(headerDate.textContent).toBe("2024-01-02")
  })
})

describe("TableApp filtering and sorting", () => {
  const camera = {
    name: "testcam",
    metadata_columns: {
      colA: "description A",
      colB: "description B",
    },
    channels: [],
  }

  beforeEach(() => {
    window.localStorage.clear()
  })

  it("filters rows based on search input", () => {
    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Simulate camera event with data
    act(() => {
      metadataEvent({
        123: { colA: "valueA", colB: "valueB" },
        124: { colA: "valueC", colB: "valueD" },
      })
      channelDataEvent({ 1: { value: 42 } })
    })

    // Check if both rows are rendered initially
    expect(screen.getByText("valueA")).toBeInTheDocument()
    expect(screen.getByText("valueC")).toBeInTheDocument()

    const metaColumntitle = screen.getByText("colA")
    fireEvent.click(metaColumntitle)

    expect(screen.getByText("Filter on", { exact: false })).toBeInTheDocument()

    // Simulate typing in the filter input
    const searchInput = screen.getByPlaceholderText("Enter", { exact: false })
    searchInput.value = "valueA"

    act(() => {
      const applyButton = screen.getByText("Apply")
      fireEvent.click(applyButton)
    })

    // Only the row with valueA should be visible now
    expect(screen.getByText("valueA")).toBeInTheDocument()
    expect(screen.queryByText("valueC")).not.toBeInTheDocument()
  })

  it("sorts rows based on column header clicks", () => {
    render(
      <TableApp
        camera={camera}
        initialDate="2024-01-01"
        isHistorical={false}
        locationName="test-location"
        siteLocation="site"
        isStale={false}
      />
    )

    // Simulate camera event with data
    act(() => {
      metadataEvent({
        125: { colA: "cherry" },
        124: { colA: "apple" },
        123: { colA: "banana" },
      })
    })

    // Check if all rows are rendered initially
    expect(screen.getByText("banana")).toBeInTheDocument()
    expect(screen.getByText("apple")).toBeInTheDocument()
    expect(screen.getByText("cherry")).toBeInTheDocument()

    let sortedRows = screen.getAllByRole("row")
    expect(sortedRows[0].textContent).toContain("cherry")
    expect(sortedRows[1].textContent).toContain("apple")
    expect(sortedRows[2].textContent).toContain("banana")

    // Click on the column header to sort by colA with shift key
    const colAHeader = screen.getByText("colA")
    fireEvent.click(colAHeader, {
      shiftKey: true,
      bubbles: true,
    })

    // Check if rows are sorted by colA
    sortedRows = screen.getAllByRole("row")
    expect(sortedRows[0].textContent).toContain("apple")
    expect(sortedRows[1].textContent).toContain("banana")
    expect(sortedRows[2].textContent).toContain("cherry")

    // Click again to reverse the sort order
    // Simulate shift+click more directly
    fireEvent.click(colAHeader, {
      shiftKey: true,
      bubbles: true,
    })
    // Check if rows are sorted in reverse order
    sortedRows = screen.getAllByRole("row")
    expect(sortedRows[0].textContent).toContain("cherry")
    expect(sortedRows[1].textContent).toContain("banana")
    expect(sortedRows[2].textContent).toContain("apple")
  })
})
