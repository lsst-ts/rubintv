import { parseJsonFromDOM, _getById } from '../modules/utils.js'
import { TableControls } from '../modules/table-control.js'
import { addToTable } from '../modules/table-auxtel.js'
import { refreshTableLoop } from '../modules/table-refresher.js'
import { auxtelDefaultSelected } from '../models.js'

window.addEventListener('load', function () {
  const meta = parseJsonFromDOM('#table-metadata')

  const tableControls = new TableControls(auxtelDefaultSelected, meta, '#table-controls', addToTable)
  addToTable(meta, tableControls.selected)

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
    addToTable(meta, selected)
  }
})
