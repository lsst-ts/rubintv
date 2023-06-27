import {
  parseJsonFromDOM,
  _getById
} from '../modules/utils.js'
import { addToTable } from '../modules/draw-simple-table.js'
import { TableControls } from '../modules/table-control.js'
import { refreshTableLoop } from '../modules/table-refresher.js'

window.addEventListener('load', function () {
  const defaultHeadersAndDescs = parseJsonFromDOM('#metadata-headers')
  const meta = parseJsonFromDOM('#table-metadata')

  const tableControls = new TableControls(
    defaultHeadersAndDescs,
    meta,
    '#table-controls',
    addToTable
  )
  addToTable(meta, tableControls.selected, defaultHeadersAndDescs)

  refreshTableLoop(injectHTML, updateTableAndControls, 5)

  /**
   * @param {{ per_day: string; table: string; }} htmlParts
   */
  function injectHTML (htmlParts) {
    _getById('per-day-refreshable').innerHTML = htmlParts.per_day
    _getById('channel-day-data').innerHTML = htmlParts.table
  }

  function updateTableAndControls (meta) {
    tableControls.updateMetadata(meta)
    tableControls.draw()
    const selected = tableControls.selected
    addToTable(meta, selected, defaultHeadersAndDescs)
  }
})
