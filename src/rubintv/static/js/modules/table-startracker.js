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

  headerGroups.forEach((group, id) => {
    const tr = $('<th>', { id: `group-${id}`, scope: 'colgroup', colspan: group.length, class: 'meta-group' })
    tr.append($('<img>', { src: '/rubintv/static/images/meta-group.png' }))
    groupRow.append(tr)
  })

  $('thead').append(groupRow)

  const headers = headerGroups.flat()
  headerGroups.forEach((group, id) => {
    const groupID = `group-${id}`
    group.forEach((attr, i) => {
      const escapedName = _escapeName(attr)
      const lastHeaderCall = $('.grid-title').last()
      const el = $('<th>', { class: `grid-title sideways ${escapedName}`, headers: groupID })
      el.text(attr)
      lastHeaderCall.after(el)
    })
  })

  // add table entries by row...
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
