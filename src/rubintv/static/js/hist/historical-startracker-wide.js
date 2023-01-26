import { parseJsonFromDOM } from '../modules/utils.js'
import { addToTable } from '../modules/table-startracker.js'
import { starTrackerWideHeaders } from '../models.js'
import { applyYearControls } from '../modules/calendar-controls.js'

window.addEventListener('DOMContentLoaded', () => {
  const meta = parseJsonFromDOM('#table-metadata')
  addToTable(meta, starTrackerWideHeaders, true)
  applyYearControls()
})
