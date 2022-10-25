/* global jQuery */
import { createTableControlUI, applySelected, parseJsonFromDOM, DefaultSelected } from './modules/table-control.js'
import { applyYearControls } from './modules/calendar-controls.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  createTableControlUI(meta, $('.channel-grid-heading'), DefaultSelected)
  applySelected(meta, DefaultSelected, true)

  applyYearControls()
})(jQuery)
