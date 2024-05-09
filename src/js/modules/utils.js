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

export function sanitiseString (str) {
  // Substitutes spaces and hyphens are exchanged for underscores.
  // Any non-word characters (any but a-z, A-Z, _) are removed.
  // Capital letters are made small.
  let sanitised = str.replace('/[\s-]/', '_')
  sanitised = sanitised.replace('[\W]','')
  return sanitised.toLowerCase()
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
