/**
* @param {string | any[]} arrayA
* @param {any} arrayB
*/
export function intersect (arrayA, arrayB) {
  return arrayA.filter(el => arrayB.includes(el))
}

/**
 * @param {RequestInfo | URL} url
 */
export async function simplePost (url) {
  const res = await fetch(url, {
    method: 'POST',
    body: ''
  })
  const data = await res.text()
  return data
}

/**
 * @param {string} tagName
 * @param {string} className
 */
export function _elWithClass (tagName, className) {
  return _elWithAttrs(tagName, { class: className })
}

/**
 * @param {string} tagName
 */
export function _elWithAttrs (tagName, attrsObj = {}) {
  const el = document.createElement(tagName)
  Object.entries(attrsObj).forEach(([attr, value]) => {
    switch (attr) {
      case 'text': {
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
export function _getById (idStr) {
  return document.getElementById(idStr)
}

const cyrb53 = (/** @type {string} */ str, seed = 0) => {
  let h1 = 0xdeadbeef ^ seed
  let h2 = 0x41c6ce57 ^ seed
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }

  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909)

  return 4294967296 * (2097151 & h2) + (h1 >>> 0)
}

/**
 * @param {string} [_attrName]
 */
function hashCacher (_attrName) {
  const cache = {}
  return function (/** @type {string} */ attrName) {
    if (cache[attrName]) {
      return cache[attrName]
    }
    const result = cyrb53(attrName)
    cache[attrName] = result
    return result
  }
}

const cachedHash = hashCacher()
/**
 * @param {string} attrName
 */
export function _escapeName (attrName) {
  return 'c_' + cachedHash(attrName)
}

/**
 * @param {string} element
 */
export function parseJsonFromDOM (element) {
  const metaInDOM = document.querySelector(element)
  if (!metaInDOM) return {}
  const metaText = document.querySelector(element).textContent
  return JSON.parse(metaText)
}

/**
 * @param {{ [x: string]: string | number }} attributes
 * @param {string} attrToCheck
 */
export function indicatorForAttr (attributes, attrToCheck) {
  // indicators are in with the attributes. they share the name of the
  // attribute they belong to, but begin with an underscore
  const indicator = `_${attrToCheck}`
  let flag = ''
  // is there an indicator for this attribute?
  if (Object.keys(attributes).includes(indicator)) {
    // if so, get its value
    flag = attributes[indicator]
  }
  return flag
}

export function replaceInString (link, dayObs, seqNum) {
  const formattedLink = link
    .replace('{dayObs}', dayObs)
    .replace('{seqNum}', seqNum.padStart(6, '0'))
  return formattedLink
}

// A helper function to mimic Jinja2's groupby
export function groupBy (array, keyFunction) {
  const obj = {}
  if (!array || array.length === 0) {
    return []
  }
  array.forEach(item => {
    const key = keyFunction(item)
    if (!obj[key]) {
      obj[key] = []
    }
    obj[key].push(item)
  })
  return Object.entries(obj)
}

export function retrieveSelected (cameraName) {
  const retrieved = localStorage.getItem(cameraName)
  return (retrieved && JSON.parse(retrieved))
}


export function getWebSockURL (name) {
  const protocol = window.location.protocol
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
  const hostname = window.location.host
  const appName = window.location.pathname.split('/')[1]
  return `${wsProtocol}//${hostname}/${appName}/${name}/`
}
