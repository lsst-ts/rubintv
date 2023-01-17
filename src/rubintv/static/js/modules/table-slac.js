import {
  createTableCell, indicatorForAttr, _getById, _elWithAttrs, _elWithClass, makeTableSortable, _escapeName
} from './utils.js'

export function addToTable (metaData, selection, sortable = false) {
  // remove existing table
  [...document.querySelectorAll('.meta')].forEach(gridElement => {
    gridElement.remove()
  })
  // add metadata headers to the table
  selection.forEach(attr => {
    const escapedName = _escapeName(attr)
    const lastHeaderCall = Array.from(document.querySelectorAll('.grid-title')).pop()
    const el = _elWithClass('th', `grid-title sideways ${escapedName}`)
    el.appendChild(document.createTextNode(attr))
    lastHeaderCall.after(el)
  })

  // add table entries by row...
  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = _getById(`seqno-${seq}`)
    // ...and column
    selection.forEach(attr => {
      const seqRowLastCell = seqRow.querySelectorAll('td:last-child')[0]
      const escapedName = _escapeName(attr)
      // check for indicator attribute (i.e. starts with '_')
      const flag = indicatorForAttr(attributes, attr)
      const el = createTableCell(attributes, attr, escapedName, flag)
      seqRowLastCell.after(el)
    })
  })

  // add empty column to table header for 'copy to clipboard'
  if (!_getById('ctbEmpty')) {
    const ctbColumnHeader = _elWithAttrs('th', { id: 'ctbEmpty' })
    // place it after the first column
    document.querySelector('.grid-title').after(ctbColumnHeader)
    // add copy to clipboard buttons to grid
    Array.from(document.querySelectorAll('tr[id^="seqno-"]')).forEach((row) => {
      const seq = row.id.split('-').pop()
      const cell = _elWithClass('td', 'grid-cell copy-to-cb')
      const button = _elWithClass('button', 'button button-table copy')
      button.setAttribute('data-seq', seq)
      cell.appendChild(button)
      row.querySelector('td').after(cell)
    })
  }

  Array.from(document.querySelectorAll('.button.copy')).forEach(button => {
    button.addEventListener('click', function () {
      const seq = this.dataset.seq
      const dateStr = _getById('the-date').dataset.date
      const dayObs = dateStr.replaceAll('-', '')
      const dataStr = `dataId = {"day_obs": ${dayObs}, "seq_num": ${seq}}`
      navigator.clipboard.writeText(dataStr)
      const responseMsg = _elWithAttrs('div', { class: 'copied', text: `DataId for ${seq} copied to clipboard` })
      const pos = this.getBoundingClientRect()
      responseMsg.setAttribute('style', `top: ${pos.y - (pos.height / 2)}px; left: ${pos.x + (pos.width + 8)}px`)
      responseMsg.addEventListener('animationend', () => {
        responseMsg.remove()
      })
      document.body.append(responseMsg)
    })
  })

  if (sortable) {
    makeTableSortable()
  }
}
