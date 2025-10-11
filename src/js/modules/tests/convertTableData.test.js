import { expect, test, describe } from "@jest/globals"
import { createTableFromStructuredData } from "../convertTableData"

describe("createTableFromStructuredData", () => {
  // Test with mixed file extensions (jpg, fits, png)
  test("converts structured data to table format with different extensions", () => {
    // Mock camera and channel data
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }, { name: "channel2" }]

    // Mock structured data similar to Python test's format
    const structuredData = {
      channel1: new Set([1, 2, 3, 4]),
      channel2: new Set([1, 2, 3]),
    }

    // Mock extension info - channel1: jpg default with fits exception, channel2: png default with fits exception
    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: { 3: "fits" },
      },
      channel2: {
        default: "png",
        exceptions: { 3: "fits" },
      },
    }

    // Call the function being tested
    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    // Verify the structure and content
    expect(Object.keys(result).length).toBe(4) // 4 sequence numbers

    // Check sequence number 1 (should have both channels)
    expect(result["1"].channel1).toBeDefined()
    expect(result["1"].channel2).toBeDefined()
    expect(result["1"].channel1.ext).toBe("jpg")
    expect(result["1"].channel2.ext).toBe("png")

    // Check sequence number 3 (should have exception extensions)
    expect(result["3"].channel1.ext).toBe("fits")
    expect(result["3"].channel2.ext).toBe("fits")

    // Check sequence number 4 (only in channel1)
    expect(result["4"].channel1).toBeDefined()
    expect(result["4"].channel2).toBeUndefined()

    // Verify file paths are correctly constructed
    expect(result["1"].channel1.key).toBe(
      "TestCamera/2024-03-10/channel1/000001/TestCamera_channel1_000001.jpg"
    )
    expect(result["3"].channel1.key).toBe(
      "TestCamera/2024-03-10/channel1/000003/TestCamera_channel1_000003.fits"
    )
  })

  // Test with string-based sequence numbers like 'final'
  test("skips non-numeric sequence numbers", () => {
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }]

    const structuredData = {
      channel1: new Set([1, 2, "final"]),
    }

    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: {},
      },
    }

    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    // Should only include numeric sequence numbers
    expect(Object.keys(result).length).toBe(2)
    expect(result["1"]).toBeDefined()
    expect(result["2"]).toBeDefined()
    expect(result["final"]).toBeUndefined()
  })

  // Test with missing extension info
  test("uses default extensions when info is missing", () => {
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }, { name: "channel2" }]

    const structuredData = {
      channel1: new Set([1, 2]),
      channel2: new Set([1]),
    }

    // Missing extension info for channel2
    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: {},
      },
      // channel2 missing intentionally
    }

    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    // Should use jpg as fallback for channel2
    expect(result["1"].channel2.ext).toBe("jpg")
  })

  // Test with empty data
  test("returns empty object when no sequence numbers found", () => {
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }]

    const structuredData = {
      channel1: new Set(), // empty set
    }

    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: {},
      },
    }

    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    expect(Object.keys(result).length).toBe(0)
  })

  // Test with array data format (simulating JSON from backend)
  test("handles array data format from JSON", () => {
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }, { name: "channel2" }]

    // Mock structured data as arrays (as it would come from JSON)
    const structuredData = {
      channel1: [1, 2, 3],
      channel2: [1, 2],
    }

    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: { 3: "fits" },
      },
      channel2: {
        default: "png",
        exceptions: {},
      },
    }

    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    // Verify structure and content
    expect(Object.keys(result).length).toBe(3)
    expect(result["1"].channel1).toBeDefined()
    expect(result["1"].channel2).toBeDefined()
    expect(result["3"].channel1).toBeDefined()
    expect(result["3"].channel2).toBeUndefined()
    expect(result["3"].channel1.ext).toBe("fits")
  })

  // Test with object format from JSON
  test("handles object data format from JSON", () => {
    const cameraName = "TestCamera"
    const dateStr = "2024-03-10"
    const channels = [{ name: "channel1" }]

    // Mock structured data as object (another possible JSON format)
    const structuredData = {
      channel1: { 1: true, 2: true, 3: true },
    }

    const extensionInfo = {
      channel1: {
        default: "jpg",
        exceptions: {},
      },
    }

    const result = createTableFromStructuredData(
      cameraName,
      dateStr,
      structuredData,
      extensionInfo,
      channels
    )

    expect(Object.keys(result).length).toBe(3)
    expect(result["1"].channel1).toBeDefined()
    expect(result["2"].channel1).toBeDefined()
    expect(result["3"].channel1).toBeDefined()
  })
})
