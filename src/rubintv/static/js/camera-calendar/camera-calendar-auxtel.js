import { TableControls } from '../modules/table-control.js'
import { parseJsonFromDOM } from '../modules/utils.js'
import { auxtelDefaultSelected } from '../models.js'
import { addToTable } from '../modules/table-auxtel.js'
import { applyYearControls } from '../modules/calendar-controls.js'

window.addEventListener('load', () => {
  const meta = parseJsonFromDOM('#table-metadata')
  const tableUI = new TableControls(auxtelDefaultSelected, meta, '.channel-grid-heading', addToTable)
  tableUI.updateMetadata(meta)
  tableUI.draw()
  addToTable(meta, tableUI.selected)
  applyYearControls()
})
