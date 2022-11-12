/* global jQuery */
import { applySelected, parseJsonFromDOM } from './modules/table-control.js'
import { applyYearControls } from './modules/calendar-controls.js'
import { startrackerDefaultSelected } from './models.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  applySelected(meta, startrackerDefaultSelected, true)
  applyYearControls()
})(jQuery)
