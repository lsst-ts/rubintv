import { makeTableSortable, createTableCell, indicatorForAttr, _escapeName, _elWithAttrs, _getById } from './utils.js'

// headerGroups is an array of arrays
export function addToTable (metaData, headerGroups, sortable = false) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return
  // add metadata group headers to the table
  // fill out the headers for the new row with blanks
  // one for each existing channel (and seq num)
  const tableRow = document.querySelector('.channel-grid tr')
  const groupRow = _elWithAttrs('tr', { id: 'grouping' })
  Array.from(tableRow.querySelectorAll('th')).forEach(() => {
    groupRow.append(_elWithAttrs('th', { scope: 'col' }))
  })

  Object.keys(headerGroups).forEach((group) => {
    const span = headerGroups[group].length
    const groupID = _escapeName(group)
    const tr = _elWithAttrs('th',
      { id: groupID, scope: 'colgroup', colspan: span, class: 'meta-group' }
    )
    tr.append(_elWithAttrs('p', { text: group }))
    tr.append(_elWithAttrs('div', {
      class: 'brace-placeholder',
      id: `brace-${groupID}`,
      style: 'height: 40px; width: 100%;'
    }))
    groupRow.append(tr)
  })

  document.querySelector('thead').prepend(groupRow)

  Object.keys(headerGroups).forEach((group) => {
    const groupID = _escapeName(group)
    headerGroups[group].forEach((attr) => {
      const escapedName = _escapeName(attr)
      const lastHeaderCall = Array.from(document.querySelectorAll('.grid-title')).pop()
      const el = _elWithAttrs('th',
        { class: `grid-title sideways ${escapedName}`, headers: groupID }
      )
      el.textContent = attr
      lastHeaderCall.after(el)
    })
  })

  // add table entries by row...
  const headers = Object.values(headerGroups).flat()
  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = _getById(`seqno-${seq}`)
    // ...and column
    headers.forEach(attr => {
      const seqRowLastCell = seqRow.querySelectorAll('td:last-child')[0]
      const escapedName = _escapeName(attr)
      // check for indicator attribute (i.e. starts with '_')
      const flag = indicatorForAttr(attributes, attr)
      const el = createTableCell(attributes, attr, escapedName, flag)
      seqRowLastCell.after(el)
    })
  })

  replaceBraceImgWithSVG()

  if (sortable) {
    makeTableSortable()
  }
}

function replaceBraceImgWithSVG () {
  const groups = document.querySelectorAll('.meta-group')
  Array.from(groups).forEach((group) => {
    const placeholder = group.querySelector('.brace-placeholder')
    placeholder.replaceWith(SVGBracket(placeholder.clientWidth))
  })
}

function SVGBracket (lineWidth) {
  const halfW = (lineWidth - 84.5) / 2
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
  svg.setAttribute('viewBox', `0 0 ${lineWidth} 38`)
  svg.setAttribute('width', '100%')
  svg.setAttribute('height', '38')
  path.setAttribute('d',
  `m1.5,38 c0,-13 8,-18 20,-18 h${halfW} c20,0 20,-20 20,-20 m1.5 0 c0,0 0,20 20, 20 h${halfW} c12,0 20,5 20,18`
  )
  path.setAttribute('fill', 'none')
  path.setAttribute('stroke', '#000')
  path.setAttribute('style', 'stroke-width: 3px')
  svg.appendChild(path)
  return svg
}
