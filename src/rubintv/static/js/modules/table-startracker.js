/* global $ */
import { makeTableSortable, createTableCell, indicatorForAttr } from './table-control.js'

// headerGroups is an array of arrays
export function addToTable (metaData, headerGroups, sortable = false) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return
  // add metadata group headers to the table
  // fill out the headers for the new row with blanks
  // one for each existing channel (and seq num)
  const tableRow = $('.channel-grid tr')
  const groupRow = $('<tr>', { id: 'grouping' })
  Array.from(tableRow.find('th')).forEach(th => {
    groupRow.append($('<th>', { scope: 'col' }))
  })

  Object.keys(headerGroups).forEach((group) => {
    const span = headerGroups[group].length
    const groupID = _escapeName(group)
    const tr = $('<th>', { id: groupID, scope: 'colgroup', colspan: span, class: 'meta-group' })
    tr.append($('<p>').text(group))
    tr.append($('<img>', { src: '/rubintv/static/images/meta-group.png' }))
    groupRow.append(tr)
  })

  $('thead').prepend(groupRow)

  Object.keys(headerGroups).forEach((group) => {
    const groupID = _escapeName(group)
    headerGroups[group].forEach((attr) => {
      const escapedName = _escapeName(attr)
      const lastHeaderCall = $('.grid-title').last()
      const el = $('<th>', { class: `grid-title sideways ${escapedName}`, headers: groupID })
      el.text(attr)
      lastHeaderCall.after(el)
    })
  })

  // add table entries by row...
  const headers = Object.values(headerGroups).flat()
  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = $(`#seqno-${seq}`)
    // ...and column
    headers.forEach(attr => {
      const seqRowLastCell = seqRow.find('td').last()
      const escapedName = _escapeName(attr)
      // check for indicator attribute (i.e. starts with '_')
      const flag = indicatorForAttr(attributes, attr)
      const el = createTableCell(attributes, attr, escapedName, flag)
      seqRowLastCell.after(el)
    })
  })
  if (sortable) {
    makeTableSortable()
  }
}

function _escapeName (displayName) {
  return displayName.toLowerCase().replaceAll(' ', '_')
}
