import "@testing-library/jest-dom"
import { isEmpty, sanitiseRedisValue } from "../utils"

/* global describe, it, expect */

describe("isEmpty", () => {
  it("should return true for empty object", () => {
    expect(isEmpty({})).toBe(true)
  })

  it("should return false for object with own properties", () => {
    expect(isEmpty({ a: 1 })).toBe(false)
    expect(isEmpty({ name: "test" })).toBe(false)
    expect(isEmpty({ value: null })).toBe(false)
    expect(isEmpty({ value: undefined })).toBe(false)
  })

  it("should return false for object with multiple properties", () => {
    expect(isEmpty({ a: 1, b: 2 })).toBe(false)
  })

  it("should return true for object with only inherited properties", () => {
    const obj = Object.create({ inherited: "value" })
    expect(isEmpty(obj)).toBe(true)
  })

  it("should return false for object with both own and inherited properties", () => {
    const obj = Object.create({ inherited: "value" })
    obj.own = "property"
    expect(isEmpty(obj)).toBe(false)
  })

  it("should return false for object with nested objects", () => {
    expect(isEmpty({ nested: {} })).toBe(false)
  })
})

describe("sanitiseRedisValue", () => {
  it("should trim whitespace from string", () => {
    expect(sanitiseRedisValue("  test  ")).toBe("TEST")
    expect(sanitiseRedisValue("\t\ntest\r\n")).toBe("TEST")
  })

  it("should remove control characters", () => {
    expect(sanitiseRedisValue("test\x00string")).toBe("TEST_STRING")
    expect(sanitiseRedisValue("test\x1Fstring")).toBe("TEST_STRING")
    expect(sanitiseRedisValue("test\x7Fstring")).toBe("TEST_STRING")
  })

  it("should replace newlines with spaces", () => {
    expect(sanitiseRedisValue("line1\nline2")).toBe("LINE1_LINE2")
    expect(sanitiseRedisValue("line1\r\nline2")).toBe("LINE1_LINE2")
    expect(sanitiseRedisValue("line1\n\nline2")).toBe("LINE1_LINE2")
  })

  it("should replace multiple spaces with single space", () => {
    expect(sanitiseRedisValue("test    multiple   spaces")).toBe(
      "TEST_MULTIPLE_SPACES"
    )
  })

  it("should replace spaces with underscores", () => {
    expect(sanitiseRedisValue("test string")).toBe("TEST_STRING")
    expect(sanitiseRedisValue("multiple word string")).toBe(
      "MULTIPLE_WORD_STRING"
    )
  })

  it("should convert to uppercase", () => {
    expect(sanitiseRedisValue("lowercase")).toBe("LOWERCASE")
    expect(sanitiseRedisValue("MixedCase")).toBe("MIXEDCASE")
  })

  it("should handle complex strings with all transformations", () => {
    expect(sanitiseRedisValue("  test\x00string\n\nwith   spaces  ")).toBe(
      "TEST_STRING_WITH_SPACES"
    )
    expect(
      sanitiseRedisValue(
        "\t\r\nComplex\x1F String\r\n\r\nWith    Everything  \t"
      )
    ).toBe("COMPLEX_STRING_WITH_EVERYTHING")
  })

  it("should handle empty string", () => {
    expect(sanitiseRedisValue("")).toBe("")
    expect(sanitiseRedisValue("   ")).toBe("")
  })

  it("should handle string with only control characters", () => {
    expect(sanitiseRedisValue("\x00\x1F\x7F")).toBe("_")
  })
})
