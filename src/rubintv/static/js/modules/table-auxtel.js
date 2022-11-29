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

  // add empty column to table header for 'copy to clipboard'
  if ($('#ctbEmpty').length === 0) {
    $('.grid-title').first().after($('<th>', { id: 'ctbEmpty' }))
    // add copy to clipboard buttons to grid
    $('tr[id^="seqno-"]').each(function () {
      const seq = this.id.split('-').pop()
      const copyButton = $('<td class="grid-cell copy-to-cb">')
        .append($('<button>', { class: 'button button-table copy' }).data('seq', seq))
      $(this).find('td').first()
        .after(copyButton)
    })
  }

  $('.button.copy').click(function () {
    const seq = $(this).data('seq')
    const dateStr = $('.the-date').attr('data-date')
    const dayObs = dateStr.replaceAll('-', '')
    const dataStr = `dataId = {"day_obs": ${dayObs}, "seq_num": ${seq}, "detector": 0}`
    navigator.clipboard.writeText(dataStr)
    const responseMsg = $('<div>', { class: 'copied' }).text(`DataId for ${seq} copied to clipboard`)
    const pos = this.getBoundingClientRect()
    responseMsg.css({ top: pos.y - (pos.height / 2), left: pos.x + (pos.width + 8) })
    $('body').append(responseMsg)
    responseMsg.delay(500).animate({ opacity: 0 }, 800, function () {
      $(this).remove()
    })
  })

  if (sortable) {
    makeTableSortable()
  }
}

function _escapeName (displayName) {
  return displayName.toLowerCase().replaceAll(' ', '_')
}
