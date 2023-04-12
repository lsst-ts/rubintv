/**
 * @param {RequestInfo | URL} url
 */
export async function getJson (url) {
  const data = getDataFromURL(url)
  return data
}

/**
 * @param {RequestInfo | URL} url
 */
export async function getHtml (url) {
  const data = getDataFromURL(url, 'text')
  return data
}

/**
 * @param {RequestInfo | URL} url
 */
async function getDataFromURL (url, dataType = 'json') {
  const res = await fetch(url)
  const data = await res[dataType]()
  return data
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
  const metaText = document.querySelector(element).textContent
  return JSON.parse(metaText)
}

/**
 * @param {{ [x: string]: string | number; }} attributes
 * @param {string | number} attr
 * @param {string[]} classes
 */
export function createTableCell (attributes, attr, ...classes) {
  const classString = classes.join(' ')
  const el = _elWithClass('td', `meta grid-cell ${classString}`)
  let val = attributes[attr]
  if (typeof val === 'number') {
    val = (+val.toFixed(3)).toString()
  }
  if (typeof val === 'undefined') {
    val = ''
  }
  el.textContent = val
  return el
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
    flag = ` ${attributes[indicator]}`
  }
  return flag
}

/**
 * @param {string} attributeName
 */
export function removeColumnFromTableFor (attributeName) {
  const cells = document.querySelectorAll('table .' + _escapeName(attributeName))
  Array.from(cells).forEach(cell => { cell.remove() })
}

export function drawTableColumnsAndRows (metaData, columns) {
  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = _getById(`seqno-${seq}`)
    if (seqRow) {
      // ...and column
      columns.forEach(attr => {
        const seqRowLastCell = seqRow.querySelectorAll('td:last-child')[0]
        const escapedName = _escapeName(attr)
        // check for indicator attribute (i.e. starts with '_')
        const flag = indicatorForAttr(attributes, attr)
        const el = createTableCell(attributes, attr, escapedName, flag)
        seqRowLastCell.after(el)
      })
    }
  })
}
