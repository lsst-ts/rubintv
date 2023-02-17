import { parseJsonFromDOM } from '../modules/utils.js'
import { TableControls } from '../modules/table-control-startracker.js'
import { drawTable } from '../modules/table-startracker.js'
import { applyYearControls } from '../modules/calendar-controls.js'

window.addEventListener('DOMContentLoaded', () => {
  const headers = parseJsonFromDOM('#metadata-headers')
  const meta = parseJsonFromDOM('#table-metadata')
  const tableControls = new TableControls(headers, meta, '.channel-grid-heading', drawTable)
  drawTable(meta, tableControls.groupedSelected)
  applyYearControls()
})
