import "@testing-library/jest-dom"
import {
  isEmpty,
  sanitiseRedisValue,
  intersect,
  union,
  sanitiseString,
  replaceInString,
  groupBy,
  toTimeString,
  getBaseFromEventUrl,
  getMediaType,
  ymdToDateStr,
  rangeSetFromLimits,
  unpackCalendarAsDateList,
  findPrevNextDate,
  indicatorForAttr,
} from "../utils"

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

describe("intersect", () => {
  it("should return common elements", () => {
    expect(intersect([1, 2, 3], [2, 3, 4])).toEqual([2, 3])
  })

  it("should return empty array when no common elements", () => {
    expect(intersect([1, 2], [3, 4])).toEqual([])
  })

  it("should return empty array when either input is empty", () => {
    expect(intersect([], [1, 2])).toEqual([])
    expect(intersect([1, 2], [])).toEqual([])
  })

  it("should work with strings", () => {
    expect(intersect(["a", "b", "c"], ["b", "c", "d"])).toEqual(["b", "c"])
  })

  it("should not deduplicate elements present multiple times in arrayA", () => {
    expect(intersect([1, 1, 2], [1, 2])).toEqual([1, 1, 2])
  })
})

describe("union", () => {
  it("should combine arrays without duplicates", () => {
    expect(union([1, 2, 3], [2, 3, 4])).toEqual([1, 2, 3, 4])
  })

  it("should return first array when second is empty", () => {
    expect(union([1, 2], [])).toEqual([1, 2])
  })

  it("should return second array when first is empty", () => {
    expect(union([], [1, 2])).toEqual([1, 2])
  })

  it("should return all elements when arrays are disjoint", () => {
    expect(union([1, 2], [3, 4])).toEqual([1, 2, 3, 4])
  })

  it("should work with strings", () => {
    expect(union(["a", "b"], ["b", "c"])).toEqual(["a", "b", "c"])
  })
})

describe("sanitiseString", () => {
  it("should replace spaces with underscores", () => {
    expect(sanitiseString("hello world")).toBe("hello_world")
  })

  it("should replace hyphens with underscores", () => {
    expect(sanitiseString("hello-world")).toBe("hello_world")
  })

  it("should convert to lowercase", () => {
    expect(sanitiseString("HelloWorld")).toBe("helloworld")
    expect(sanitiseString("UPPER")).toBe("upper")
  })

  it("should remove non-word characters", () => {
    expect(sanitiseString("hello!world")).toBe("helloworld")
    expect(sanitiseString("test@#$%")).toBe("test")
  })

  it("should handle mixed transformations", () => {
    expect(sanitiseString("Hello-World 123!")).toBe("hello_world_123")
  })

  it("should preserve underscores", () => {
    expect(sanitiseString("already_snake")).toBe("already_snake")
  })
})

describe("replaceInString", () => {
  it("should replace {dayObs} and {seqNum:06}", () => {
    expect(
      replaceInString("obs/{dayObs}/{seqNum:06}", "2024-01-15", "42")
    ).toBe("obs/20240115/000042")
  })

  it("should pad seqNum to 6 digits", () => {
    expect(replaceInString("{seqNum:06}", "2024-01-15", "1")).toBe("000001")
    expect(replaceInString("{seqNum:06}", "2024-01-15", "123456")).toBe(
      "123456"
    )
  })

  it("should strip hyphens from dayObs", () => {
    expect(replaceInString("{dayObs}", "2024-01-15", "1")).toBe("20240115")
  })

  it("should replace {dev} with empty string when not dev instance", () => {
    expect(replaceInString("app{dev}.example.com", "2024-01-15", "1")).toBe(
      "app.example.com"
    )
  })

  it("should replace {dev} with -dev when isDevInstance is true", () => {
    expect(
      replaceInString("app{dev}.example.com", "2024-01-15", "1", {
        isDevInstance: true,
      })
    ).toBe("app-dev.example.com")
  })

  it("should map siteLocation summit to cp", () => {
    expect(
      replaceInString("{siteLoc}.example.com", "2024-01-15", "1", {
        siteLocation: "summit",
      })
    ).toBe("cp.example.com")
  })

  it("should map siteLocation base to ls", () => {
    expect(
      replaceInString("{siteLoc}.example.com", "2024-01-15", "1", {
        siteLocation: "base",
      })
    ).toBe("ls.example.com")
  })

  it("should use empty string for unknown siteLocation", () => {
    expect(
      replaceInString("{siteLoc}.example.com", "2024-01-15", "1", {
        siteLocation: "unknown",
      })
    ).toBe(".example.com")
  })

  it("should replace {controller} with provided controller", () => {
    expect(
      replaceInString("{controller}", "2024-01-15", "1", {
        controller: "main",
      })
    ).toBe("main")
  })

  it("should use default value when controller is empty", () => {
    expect(
      replaceInString("{controller:default=fallback}", "2024-01-15", "1")
    ).toBe("fallback")
  })

  it("should prefer explicit controller over default", () => {
    expect(
      replaceInString("{controller:default=fallback}", "2024-01-15", "1", {
        controller: "primary",
      })
    ).toBe("primary")
  })
})

describe("groupBy", () => {
  it("should group items by key function", () => {
    const items = [
      { type: "a", val: 1 },
      { type: "b", val: 2 },
      { type: "a", val: 3 },
    ]
    const result = groupBy(items, (i) => i.type)
    expect(result).toEqual([
      [
        "a",
        [
          { type: "a", val: 1 },
          { type: "a", val: 3 },
        ],
      ],
      ["b", [{ type: "b", val: 2 }]],
    ])
  })

  it("should return empty array for empty input", () => {
    expect(groupBy([], (i) => i)).toEqual([])
  })

  it("should return empty array for null/undefined input", () => {
    expect(groupBy(null, (i) => i)).toEqual([])
    expect(groupBy(undefined, (i) => i)).toEqual([])
  })

  it("should handle all items in same group", () => {
    const result = groupBy([1, 2, 3], () => "same")
    expect(result).toEqual([["same", [1, 2, 3]]])
  })
})

describe("toTimeString", () => {
  it("should format zero as 00:00:00", () => {
    expect(toTimeString(0)).toBe("00:00:00")
  })

  it("should format seconds correctly", () => {
    expect(toTimeString(5000)).toBe("00:00:05")
    expect(toTimeString(59000)).toBe("00:00:59")
  })

  it("should format minutes correctly", () => {
    expect(toTimeString(60000)).toBe("00:01:00")
    expect(toTimeString(90000)).toBe("00:01:30")
  })

  it("should format hours correctly", () => {
    expect(toTimeString(3600000)).toBe("01:00:00")
    expect(toTimeString(3661000)).toBe("01:01:01")
  })

  it("should prefix negative values with -", () => {
    expect(toTimeString(-5000)).toBe("-00:00:05")
    expect(toTimeString(-3661000)).toBe("-01:01:01")
  })

  it("should handle large hour values", () => {
    expect(toTimeString(36000000)).toBe("10:00:00")
  })
})

describe("getBaseFromEventUrl", () => {
  it("should strip the last path segment and ensure trailing slash", () => {
    expect(getBaseFromEventUrl("http://example.com/a/b/file.jpg")).toBe(
      "http://example.com/a/b/"
    )
  })

  it("should handle URL with single path segment", () => {
    expect(getBaseFromEventUrl("http://example.com/file.jpg")).toBe(
      "http://example.com/"
    )
  })

  it("should not double trailing slash", () => {
    const result = getBaseFromEventUrl("http://example.com/a/b/c")
    expect(result.endsWith("/")).toBe(true)
    expect(result).toBe("http://example.com/a/b/")
  })
})

describe("getMediaType", () => {
  it("should return video for mp4", () => {
    expect(getMediaType("mp4")).toBe("video")
  })

  it("should return video for mov", () => {
    expect(getMediaType("mov")).toBe("video")
  })

  it("should return image for jpg", () => {
    expect(getMediaType("jpg")).toBe("image")
  })

  it("should return image for png", () => {
    expect(getMediaType("png")).toBe("image")
  })

  it("should default to image for unknown extensions", () => {
    expect(getMediaType("pdf")).toBe("image")
    expect(getMediaType("")).toBe("image")
  })
})

describe("ymdToDateStr", () => {
  it("should format year, month, day into ISO date string", () => {
    expect(ymdToDateStr(2024, 1, 15)).toBe("2024-01-15")
  })

  it("should pad single-digit month and day", () => {
    expect(ymdToDateStr(2024, 1, 1)).toBe("2024-01-01")
    expect(ymdToDateStr(2024, 9, 5)).toBe("2024-09-05")
  })

  it("should handle two-digit month and day without extra padding", () => {
    expect(ymdToDateStr(2024, 12, 31)).toBe("2024-12-31")
  })
})

describe("rangeSetFromLimits", () => {
  it("should return a set of numbers from start to end inclusive", () => {
    expect(rangeSetFromLimits([1, 5])).toEqual(new Set([1, 2, 3, 4, 5]))
  })

  it("should return a single-element set when start equals end", () => {
    expect(rangeSetFromLimits([3, 3])).toEqual(new Set([3]))
  })

  it("should return empty set when no argument given", () => {
    expect(rangeSetFromLimits()).toEqual(new Set())
  })

  it("should return empty set for undefined", () => {
    expect(rangeSetFromLimits(undefined)).toEqual(new Set())
  })
})

describe("unpackCalendarAsDateList", () => {
  it("should return sorted list of ISO date strings from calendar data", () => {
    const calendar = {
      2024: {
        1: { 5: 1, 10: 1 },
        12: { 1: 1 },
      },
    }
    expect(unpackCalendarAsDateList(calendar)).toEqual([
      "2024-01-05",
      "2024-01-10",
      "2024-12-01",
    ])
  })

  it("should sort dates across years", () => {
    const calendar = {
      2025: { 1: { 1: 1 } },
      2024: { 12: { 31: 1 } },
    }
    const result = unpackCalendarAsDateList(calendar)
    expect(result[0]).toBe("2024-12-31")
    expect(result[1]).toBe("2025-01-01")
  })

  it("should return empty array for empty calendar", () => {
    expect(unpackCalendarAsDateList({})).toEqual([])
  })
})

describe("findPrevNextDate", () => {
  const dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]

  it("should return prev and next for a middle date", () => {
    expect(findPrevNextDate(dates, "2024-01-02")).toEqual({
      prevDate: "2024-01-01",
      nextDate: "2024-01-03",
    })
  })

  it("should return null prevDate for the first date", () => {
    expect(findPrevNextDate(dates, "2024-01-01")).toEqual({
      prevDate: null,
      nextDate: "2024-01-02",
    })
  })

  it("should return null nextDate for the last date", () => {
    expect(findPrevNextDate(dates, "2024-01-04")).toEqual({
      prevDate: "2024-01-03",
      nextDate: null,
    })
  })

  it("should return both null when date is not in list", () => {
    expect(findPrevNextDate(dates, "2024-01-99")).toEqual({
      prevDate: null,
      nextDate: null,
    })
  })
})

describe("indicatorForAttr", () => {
  it("should return indicator value when present", () => {
    const attrs = { exposure: "30s", _exposure: "warn" }
    expect(indicatorForAttr(attrs, "exposure")).toBe("warn")
  })

  it("should return empty string when no indicator present", () => {
    const attrs = { exposure: "30s" }
    expect(indicatorForAttr(attrs, "exposure")).toBe("")
  })

  it("should return empty string for unknown attribute", () => {
    expect(indicatorForAttr({}, "anything")).toBe("")
  })

  it("should not confuse indicator for a different attribute", () => {
    const attrs = { _other: "flag" }
    expect(indicatorForAttr(attrs, "exposure")).toBe("")
  })
})
