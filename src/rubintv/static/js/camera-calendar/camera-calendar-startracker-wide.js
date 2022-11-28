/* global jQuery */
import { parseJsonFromDOM } from '../modules/table-control.js'
import { addToTable } from '../modules/table-startracker.js'
import { starTrackerWideHeaders } from '../models.js'
import { applyYearControls } from '../modules/calendar-controls.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  addToTable(meta, starTrackerWideHeaders, true)
  applyYearControls()
})(jQuery)
