import { gunzipSync } from "fflate"
import { homeUrl, imagesUrl } from "../config"
import { ExposureEvent, MetadataRow } from "../components/componentTypes"

export function isEmpty(obj: Record<string, unknown>): boolean {
  for (const prop in obj) {
    if (Object.hasOwn(obj, prop)) {
      return false
    }
  }

  return true
}

export function intersect<T>(arrayA: T[], arrayB: T[]): T[] {
  return arrayA.filter((el) => arrayB.includes(el))
}

export function union<T>(arrayA: T[], arrayB: T[]): T[] {
  return arrayA.concat(arrayB.filter((el) => !arrayA.includes(el)))
}

export async function simplePost(
  url: RequestInfo | URL,
  message: object = {}
): Promise<string> {
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(message),
  })
  const data = await res.text()
  if (!res.ok) {
    throw new Error(`HTTP error ${res.status}: ${data}`)
  }
  return data
}

export async function simpleGet(
  url: string | URL,
  params: Record<string, string> = {}
): Promise<string> {
  const urlObj = new URL(url)
  Object.entries(params).forEach(([key, value]) => {
    urlObj.searchParams.append(key, value)
  })
  const res = await fetch(urlObj.toString())
  if (!res.ok) {
    throw new Error(`HTTP error for ${url}: ${res.status}`)
  }
  const data = await res.text()
  return data
}

export function _elWithClass(tagName: string, className: string): HTMLElement {
  return _elWithAttrs(tagName, { class: className })
}

export function _elWithAttrs(
  tagName: string,
  attrsObj: Record<string, string> = {}
): HTMLElement {
  const el = document.createElement(tagName)
  Object.entries(attrsObj).forEach(([attr, value]) => {
    switch (attr) {
      case "text": {
        const tNode = document.createTextNode(value)
        el.appendChild(tNode)
        break
      }
      default:
        el.setAttribute(attr, value)
    }
  })
  return el
}

export function _getById(idStr: string): HTMLElement | null {
  return document.getElementById(idStr)
}

export function indicatorForAttr(
  attributes: MetadataRow,
  attrToCheck: string
): string {
  // indicators are in with the attributes. they share the name of the
  // attribute they belong to, but begin with an underscore
  const indicator = `_${attrToCheck}`
  let flag = ""
  // is there an indicator for this attribute?
  if (Object.keys(attributes).includes(indicator)) {
    // if so, get its value
    flag = attributes[indicator] as string
  }
  return flag
}

export function sanitiseString(str: string): string {
  // Substitutes spaces and hyphens are exchanged for underscores.
  // Any non-word characters (any but a-z, A-Z, _) are removed.
  // Capital letters are made small.
  let sanitised = str.replace(/[\s-]/g, "_")
  sanitised = sanitised.replace(/[\W]/g, "")
  return sanitised.toLowerCase()
}

interface ReplaceOptions {
  siteLocation?: string
  controller?: string
}

export function replaceInString(
  link: string,
  dayObs: string,
  seqNum: string,
  { siteLocation = "", controller = "" }: ReplaceOptions = {}
): string {
  interface SiteLocMap {
    [key: string]: string
    summit: string
    base: string
  }

  const siteLocToDomain = (siteLocation: keyof SiteLocMap | string): string => {
    // Maps site location to domain
    // can only be summit or base
    const siteLocMap: SiteLocMap = {
      summit: "cp",
      base: "ls",
    }
    return siteLocMap[siteLocation] || ""
  }
  const formattedLink = link
    .replace("{siteLoc}", siteLocToDomain(siteLocation))
    .replace(
      /{controller(:default=(\w+))?}/,
      (_, __, defaultValue) => controller || defaultValue || ""
    )
    .replace("{dayObs}", dayObs)
    .replace("{seqNum}", seqNum.padStart(6, "0"))
  return formattedLink
}

// A helper function to mimic Jinja2's groupby
export function groupBy<T>(
  array: T[],
  keyFunction: (item: T) => string
): [string, T[]][] {
  const obj: { [key: string]: T[] } = {}
  if (!array || array.length === 0) {
    return []
  }
  array.forEach((item) => {
    const key = keyFunction(item)
    if (!obj[key]) {
      obj[key] = []
    }
    obj[key].push(item)
  })
  return Object.entries(obj)
}

export const STORAGE_VERSION = "1"

export function retrieveStoredSelection(
  storageKey: string,
  version = STORAGE_VERSION
) {
  const stored = localStorage.getItem(storageKey)
  if (!stored) return null

  try {
    // Check if we have versioned data
    const data = JSON.parse(stored)
    if (typeof data === "object" && data.version && data.columns) {
      // We have versioned data
      return data.columns
    }
    // Convert old format to new
    const columns = Array.isArray(data) ? data : null
    if (columns) {
      storeSelected(columns, storageKey, version)
      return columns
    }
    return null
  } catch (e) {
    console.error(`Error parsing stored selection for ${storageKey}:`, e)
    return null
  }
}

export function storeSelected(
  columns: string[],
  cameraName: string,
  version = STORAGE_VERSION
) {
  if (!Array.isArray(columns)) return
  localStorage.setItem(
    cameraName,
    JSON.stringify({
      version,
      columns,
    })
  )
}

export function getWebSockURL(name: string): string {
  const protocol = window.location.protocol
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:"
  const hostname = window.location.host
  const appName = window.location.pathname.split("/")[1]
  return `${wsProtocol}//${hostname}/${appName}/${name}/`
}

export function getStrHashCode(str: string): number {
  let hash = 0,
    i = 0
  const len = str.length
  while (i < len) {
    hash = ((hash << 5) - hash + str.charCodeAt(i++)) << 0
  }
  return hash
}

export const decodeUnpackWSPayload = (compressed: string): string => {
  let data
  try {
    // Decode Base64 string to Uint8Array
    const binaryString = atob(compressed)
    const len = binaryString.length
    const bytes = new Uint8Array(len)

    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }

    // Decompress the gzip data
    const decompressed = gunzipSync(bytes)

    // Convert Uint8Array to a string
    const textDecoder = new TextDecoder()
    data = JSON.parse(textDecoder.decode(decompressed))
  } catch (error) {
    console.error("Error decompressing payload:", error)
    data = {
      error: "Couldn't decompress payload",
    }
  }
  return data
}

export const toTimeString = (period: number): string => {
  /*  Takes a length of time in ms and converts to string `"HH:MM:SS"`.
      This allows for negative times to compensate for any bug that
      reckons that past events are yet to happen.
  */
  const absPeriod = Math.abs(period) // Absolute value for formatting

  // Extract hours, minutes, and seconds from the absolute period
  const hours = Math.floor(absPeriod / (1000 * 60 * 60))
  const minutes = Math.floor((absPeriod % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((absPeriod % (1000 * 60)) / 1000)

  // Format time with leading zeros
  const timeString = `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`

  // Add "-" prefix for negative periods
  return period < 0 ? `-${timeString}` : timeString
}

export function getBaseFromEventUrl(url: string): string {
  let baseImgUrl = url.split("/").slice(0, -1).join("/")
  if (!baseImgUrl.endsWith("/")) {
    baseImgUrl += "/"
  }
  return baseImgUrl
}

export function getMediaType(ext: string): "video" | "image" {
  if (["mp4", "mov"].includes(ext)) {
    return "video"
  }
  return "image" // default to image
}

export const monthNames: readonly string[] = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

export const ymdToDateStr = (
  year: number,
  month: number,
  day: number
): string => `${year}-${("0" + month).slice(-2)}-${("0" + day).slice(-2)}`

export async function getHistoricalData(
  locationName: string,
  cameraName: string,
  date: string
): Promise<string> {
  // Fetches historical data for a given location, camera, and date.
  const apiUrl = new URL(
    `api/${locationName}/${cameraName}/date/${date}`,
    homeUrl
  )
  const data = await simpleGet(apiUrl.toString())
  return data
}

export function getMediaProxyUrl(
  mediaType: string,
  locationName: string,
  cameraName: string,
  channelName: string,
  filename: string
): string {
  // Constructs a URL for a media file (image or video) for a given location name,
  // camera name, channel name, and filename.
  return new URL(
    `event_${mediaType}/${locationName}/${cameraName}/${channelName}/${filename}`,
    homeUrl
  ).toString()
}

export const getImageAssetUrl = (path: string): string => {
  const [base, queriesMaybe] = imagesUrl.split("?")
  const queries = queriesMaybe ? "?" + queriesMaybe : ""
  return new URL(path + queries, base + "/").toString()
}

export const setCameraBaseUrl = (locationName: string, cameraName: string) => {
  const cameraBaseUrl = new URL(`${locationName}/${cameraName}/`, homeUrl)
  return {
    getEventUrl: (event: ExposureEvent) => {
      const { channel_name, day_obs, seq_num } = event
      return new URL(
        `event?channel_name=${channel_name}&date_str=${day_obs}&seq_num=${seq_num}`,
        cameraBaseUrl
      ).toString()
    },
  }
}

export const getCameraPageForDateUrl = (
  locationName: string,
  cameraName: string,
  date: string
): string => {
  // Constructs a URL for the camera page for a specific date.
  return new URL(
    `${locationName}/${cameraName}/date/${date}`,
    homeUrl
  ).toString()
}
