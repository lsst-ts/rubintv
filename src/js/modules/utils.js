import { gunzipSync } from "fflate"

/**
 * @param {any[]} arrayA
 * @param {any[]} arrayB
 */
export function intersect(arrayA, arrayB) {
  return arrayA.filter((el) => arrayB.includes(el))
}

/**
 * @param {any[]} arrayA
 * @param {any[]} arrayB
 */
export function union(arrayA, arrayB) {
  return arrayA.concat(arrayB.filter((el) => !arrayA.includes(el)))
}

/**
 * @param {RequestInfo | URL} url
 * @param {Object} message
 */
export async function simplePost(url, message = {}) {
  const res = await fetch(url, {
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

/**
 * @param {RequestInfo | URL} url
 */
export async function simpleGet(url, params = {}) {
  const urlObj = new URL(url)
  Object.entries(params).forEach(([key, value]) => {
    urlObj.searchParams.append(key, value)
  })
  const res = await fetch(urlObj)
  if (!res.ok) {
    throw new Error(`HTTP error for ${url}: ${res.status}`)
  }
  const data = await res.text()
  return data
}

/**
 * @param {string} tagName
 * @param {string} className
 */
export function _elWithClass(tagName, className) {
  return _elWithAttrs(tagName, { class: className })
}

/**
 * @param {string} tagName
 */
export function _elWithAttrs(tagName, attrsObj = {}) {
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

/**
 * @param {string} idStr
 */
export function _getById(idStr) {
  return document.getElementById(idStr)
}

/**
 * @param {{ [x: string]: string | number }} attributes
 * @param {string} attrToCheck
 */
export function indicatorForAttr(attributes, attrToCheck) {
  // indicators are in with the attributes. they share the name of the
  // attribute they belong to, but begin with an underscore
  const indicator = `_${attrToCheck}`
  let flag = ""
  // is there an indicator for this attribute?
  if (Object.keys(attributes).includes(indicator)) {
    // if so, get its value
    flag = attributes[indicator]
  }
  return flag
}

export function sanitiseString(str) {
  // Substitutes spaces and hyphens are exchanged for underscores.
  // Any non-word characters (any but a-z, A-Z, _) are removed.
  // Capital letters are made small.
  let sanitised = str.replaceAll(/[\s-]/g, "_")
  sanitised = sanitised.replaceAll(/[\W]/g, "")
  return sanitised.toLowerCase()
}

export function replaceInString(
  link,
  dayObs,
  seqNum,
  { siteLoc = "", controller = "" } = {}
) {
  const siteLocToDomain = (siteLoc) => {
    // Maps site location to domain
    // can only be summit or base
    const siteLocMap = {
      summit: "cp",
      base: "ls",
    }
    return siteLocMap[siteLoc] || ""
  }
  const formattedLink = link
    .replace("{siteLoc}", siteLocToDomain(siteLoc))
    .replace(
      /{controller(:default=(\w+))?}/,
      (_, __, defaultValue) => controller || defaultValue || ""
    )
    .replace("{dayObs}", dayObs)
    .replace("{seqNum}", seqNum.padStart(6, "0"))
  return formattedLink
}

// A helper function to mimic Jinja2's groupby
export function groupBy(array, keyFunction) {
  const obj = {}
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

export function retrieveSelected(cameraName) {
  const retrieved = localStorage.getItem(cameraName)
  return retrieved && JSON.parse(retrieved)
}

export function getWebSockURL(name) {
  const protocol = window.location.protocol
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:"
  const hostname = window.location.host
  const appName = window.location.pathname.split("/")[1]
  return `${wsProtocol}//${hostname}/${appName}/${name}/`
}

export function getStrHashCode(str) {
  let hash = 0,
    i = 0,
    len = str.length
  while (i < len) {
    hash = ((hash << 5) - hash + str.charCodeAt(i++)) << 0
  }
  return hash
}

export const decodeUnpackWSPayload = (compressed) => {
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
    data = {
      error: "Couldn't decompress payload",
    }
  }
  return data
}

export const toTimeString = (period) => {
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

export function getBaseFromEventUrl(url) {
  let baseImgUrl = url.split("/").slice(0, -1).join("/")
  if (!baseImgUrl.endsWith("/")) {
    baseImgUrl += "/"
  }
  return baseImgUrl
}

export function getMediaType(ext) {
  if (["mp4", "mov"].includes(ext)) {
    return "video"
  }
  return "image" // default to image
}

export const monthNames = [
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

/**
 * Converts numerical year, month, and day to a string in the format YYYY-MM-DD.
 * The month and day are zero-padded to two digits.
 * @param {number} year
 * @param {number} month
 * @param {number} day
 * @returns {string} - A string in the format YYYY-MM-DD
 */
export const ymdToDateStr = (year, month, day) =>
  `${year}-${("0" + month).slice(-2)}-${("0" + day).slice(-2)}`

/**
 *
 * @param {string} locationName
 * @param {string} cameraName
 * @param {string} date
 * @returns {Promise<string>} - Returns encoded json string of historical
 * data for a given location, camera, and date.
 */
export async function getHistoricalData(locationName, cameraName, date) {
  // Returns the historical data URL for a given location, camera, and date
  const { homeUrl } = window.APP_DATA
  const APIUrl = new URL(
    `api/${locationName}/${cameraName}/date/${date}`,
    homeUrl
  )
  const data = await simpleGet(APIUrl)
  return data
}

/**
 *
 * @param {string} mediaType
 * @param {string} locationName
 * @param {string} cameraName
 * @param {string} channelName
 * @param {string} filename
 * @returns {URL} - Returns the URL for a media file (image or video) for a given
 * location and camera
 */
export function getMediaProxyUrl(
  mediaType,
  locationName,
  cameraName,
  channelName,
  filename
) {
  // Returns the URL for a media file (image or video) for a given location and camera
  const { homeUrl } = window.APP_DATA
  return new URL(
    `event_${mediaType}/${locationName}/${cameraName}/${channelName}/${filename}`,
    homeUrl
  )
}
