/* global jQuery */
import { createTableControlUI, applySelected, parseJsonFromDOM } from './modules/table-control.js'
import { applyYearControls } from './modules/calendar-controls.js'
import { auxtelDefaultSelected } from './models.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  createTableControlUI(meta, $('.channel-grid-heading'), auxtelDefaultSelected)
  applySelected(meta, auxtelDefaultSelected, true)

  applyYearControls()
})(jQuery)
