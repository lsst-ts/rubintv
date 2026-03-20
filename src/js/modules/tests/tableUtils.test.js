import "@testing-library/jest-dom"
import { getAllColumnNames, getDefaultColumns } from "../tableUtils"

/* global describe, it, expect */

describe("getAllColumnNames", () => {
  it("should return all column names including default and available columns", () => {
    const metadata = {
      1: { "Column 1": "data" },
      2: { "Column 2": "data" },
    }
    const defaultColNames = ["Column 1"]

    const result = getAllColumnNames(metadata, defaultColNames)
    expect(result).toEqual(["Column 1", "Column 2"])
  })

  it("should return all column names when there are no non-selectable columns", () => {
    const metadata = {
      1: { "Column 1": "data" },
      2: { "Column 2": "data" },
    }
    const defaultColNames = ["Column 1", "Column 2"]
    const nonSelectableCols = []

    const result = getAllColumnNames(
      metadata,
      defaultColNames,
      nonSelectableCols
    )
    expect(result).toEqual(["Column 1", "Column 2"])
  })

  it("should return empty array when there are no columns in metadata", () => {
    const metadata = {}
    const defaultColNames = []
    const nonSelectableCols = []

    const result = getAllColumnNames(
      metadata,
      defaultColNames,
      nonSelectableCols
    )
    expect(result).toEqual([])
  })
})

describe("getDefaultColumns", () => {
  it("should return default columns based on camera metadata", () => {
    const camera = {
      metadata_columns: {
        "Column 1": "Description 1",
        "Column 2": "Description 2",
      },
    }

    const result = getDefaultColumns(camera)
    expect(result).toEqual([
      { name: "Column 1", desc: "Description 1" },
      { name: "Column 2", desc: "Description 2" },
    ])
  })

  it("should return empty array when camera has no metadata columns", () => {
    const camera = {
      metadata_columns: null,
    }

    const result = getDefaultColumns(camera)
    expect(result).toEqual([])
  })
})
