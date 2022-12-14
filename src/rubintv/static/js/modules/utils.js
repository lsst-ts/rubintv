export async function getJson (url) {
  const data = getDataFromURL(url)
  return data
}

export async function getHtml (url) {
  const data = getDataFromURL(url, 'text')
  return data
}

async function getDataFromURL (url, dataType = 'json') {
  const res = await fetch(url)
  const data = await res[dataType]()
  return data
}

export async function simplePost (url) {
  const res = await fetch(url, {
    method: 'POST',
    body: ''
  })
  const data = await res.text()
  return data
}

export function _elWithClass (tagName, className) {
  return _elWithAttrs(tagName, { class: className })
}

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

export function _getById (idStr) {
  return document.getElementById(idStr)
}

export function _escapeName (displayName) {
  return displayName.toLowerCase().replaceAll(' ', '_')
}

export function parseJsonFromDOM (element) {
  const metaText = document.querySelector(element).text
  return JSON.parse(metaText)
}

export function createTableCell (attributes, attr, ...classes) {
  const classString = classes.join(' ')
  const el = _elWithClass('td', `meta grid-cell ${classString}`)
  let val = attributes[attr]
  if (typeof val === 'number') {
    val = (+val.toFixed(3))
  }
  if (typeof val === 'undefined') {
    val = ''
  }
  el.textContent = val
  return el
}

export function indicatorForAttr (attributes, attr) {
  const indicator = `_${attr}`
  let flag = ''
  // eslint-disable-next-line no-prototype-builtins
  if (attributes.hasOwnProperty(indicator)) {
    // add it to group for including in the class list
    // possible values include 'bad' and 'warning'
    flag = ` ${attributes[indicator]}`
  }
  return flag
}

export function removeColumnFromTableFor (attributeName) {
  const cells = document.querySelectorAll('table .' + _escapeName(attributeName))
  Array.from(cells).forEach(cell => { cell.remove() })
}

export function makeTableSortable () {
  document.querySelectorAll('th').forEach(thElem => {
    let asc = true
    const index = Array.from(thElem.parentNode.children).indexOf(thElem)
    thElem.addEventListener('click', (e) => {
      const arr = [...thElem.closest('table').querySelectorAll('tbody tr')]
      arr.sort((a, b) => {
        let aVal = a.children[index].innerText
        let bVal = b.children[index].innerText
        if (!isNaN(aVal) && !isNaN(bVal)) {
          aVal = +aVal
          bVal = +bVal
          return (asc) ? aVal > bVal : aVal < bVal
        }
        return (asc) ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      })
      arr.forEach(elem => {
        thElem.closest('table').querySelector('tbody').appendChild(elem)
      })
      asc = !asc
    })
  })
}
