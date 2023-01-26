import { parseJsonFromDOM } from '../modules/table-control.js'
import { addToTable } from '../modules/table-startracker.js'
import { starTrackerFastHeaders } from '../models.js'
import { applyYearControls } from '../modules/calendar-controls.js'

window.addEventListener('load', () => {
  const meta = parseJsonFromDOM('#table-metadata')
  addToTable(meta, starTrackerFastHeaders, true)
  applyYearControls()
})
