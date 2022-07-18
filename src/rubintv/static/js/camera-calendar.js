/* global jQuery */
import { createTableControlUI, applySelected, loadMetadata, DefaultSelected } from './modules/table-control.js'
import { applyYearControls } from './modules/calendar-controls.js'

(function ($) {
  const meta = loadMetadata()
  createTableControlUI(meta, $('.channel-grid-heading'), DefaultSelected)
  applySelected(meta, DefaultSelected, true)

  applyYearControls()
})(jQuery)
