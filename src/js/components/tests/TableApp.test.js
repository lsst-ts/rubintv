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
  _getById: (id) => {
    if (id === "table") {
      return { scrollIntoView: jest.fn() }
    }
    if (id === "header-date") {
      return {
        textContent: "",
        classList: {
          remove: jest.fn(),
        },
      }
    }
    return null
  },
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

    const { container } = render(
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
