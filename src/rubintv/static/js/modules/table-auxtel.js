/* global $ */
import { makeTableSortable, createTableCell, indicatorForAttr } from './table-control.js'

export function addToTable (metaData, selection, sortable = false) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return
  // add metadata headers to the table
  selection.forEach(attr => {
    const escapedName = _escapeName(attr)
    const lastHeaderCall = $('.grid-title').last()
    const el = $('<th>', { class: `grid-title sideways ${escapedName}` })
    el.text(attr)
    lastHeaderCall.after(el)
  })

  // add table entries by row...
  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = $(`#seqno-${seq}`)
    // ...and column
    selection.forEach(attr => {
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
