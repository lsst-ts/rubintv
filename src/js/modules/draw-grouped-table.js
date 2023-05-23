import {
  _escapeName,
  _elWithAttrs,
  drawTableColumnsAndRows
} from './utils.js'

// headerGroups is an array of arrays
/**
 * @param {{[s: string]: any;} | ArrayLike<any>} metaData
 * @param {ArrayLike<any> | { [s: string]: any; }} headerGroups
 */
export function drawTable (metaData, headerGroups) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return

  // remove existing metadata part of table
  Array.from(document.querySelectorAll('.meta')).forEach(gridElement => {
    gridElement.remove()
  })

  // add metadata group headers to the table
  // fill out the headers for the new row with blanks
  // one for each existing channel (and seq num)
  const tableRow = document.querySelector('.channel-grid tr')
  const groupRow = _elWithAttrs('tr', { id: 'grouping', class: 'meta' })
  Array.from(tableRow.querySelectorAll('th')).forEach(() => {
    groupRow.append(_elWithAttrs('th', { scope: 'col' }))
  })

  Object.keys(headerGroups).forEach((group) => {
    const span = Object.keys(headerGroups[group]).length
    if (span > 0) {
      const groupID = _escapeName(group)
      const tr = _elWithAttrs('th',
        { id: groupID, scope: 'colgroup', colspan: span, class: 'meta-group' }
      )
      tr.append(_elWithAttrs('p', { class: 'braced-group-title', text: group }))
      tr.append(_elWithAttrs('div', {
        class: 'brace-placeholder',
        id: `brace-${groupID}`,
        style: 'height: 40px; width: 100%;'
      }))
      groupRow.append(tr)
    }
  })

  document.querySelector('thead').prepend(groupRow)

  Object.keys(headerGroups).forEach((group) => {
    const groupID = _escapeName(group)
    Object.keys(headerGroups[group]).forEach((/** @type {string} */ attr) => {
      const escapedName = _escapeName(attr)
      const lastHeaderCall = Array.from(document.querySelectorAll('.grid-title')).pop()
      const el = _elWithAttrs('th',
        { class: `grid-title sideways meta ${escapedName}`, headers: groupID }
      )
      el.textContent = attr
      if (headerGroups[group][attr]) {
        el.title = headerGroups[group][attr]
      }
      lastHeaderCall.after(el)
    })
  })

  // add table entries by row...
  const headers = Object.values(headerGroups).map(h => Object.keys(h)).flat()
  drawTableColumnsAndRows(metaData, headers)

  replaceBraceImgWithSVG()
}

function replaceBraceImgWithSVG () {
  const groups = document.querySelectorAll('.meta-group')
  Array.from(groups).forEach((group) => {
    const placeholder = group.querySelector('.brace-placeholder')
    placeholder.replaceWith(SVGBracket(placeholder.clientWidth))
  })
}

/**
 * @param {number} width
 */
function SVGBracket (width) {
  // draws a curly brace on it's side the total length of width
  // note, if the width less than 84.5px, it will look strange
  const half = (width - 84.5) / 2
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
  svg.setAttribute('viewBox', `0 0 ${width} 38`)
  svg.setAttribute('width', '100%')
  svg.setAttribute('height', '38')
  path.setAttribute('d',
  `m1.5,38 c0,-13 8,-18 20,-18 h${half} c20,0 20,-20 20,-20 m1.5 0 c0,0 0,20 20, 20 h${half} c12,0 20,5 20,18`
  )
  path.setAttribute('fill', 'none')
  path.setAttribute('class', 'svg-brace')
  path.setAttribute('style', 'stroke-width: 1.5px')
  svg.appendChild(path)
  return svg
}
