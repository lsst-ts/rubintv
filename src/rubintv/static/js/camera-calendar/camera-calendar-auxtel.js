/* global jQuery */
import { createTableControlUI, parseJsonFromDOM, addDownloadMetadataButton } from '../modules/table-control.js'
import { auxtelDefaultSelected } from '../models.js'
import { addToTable } from '../modules/table-auxtel.js'
import { applyYearControls } from '../modules/calendar-controls.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  createTableControlUI(meta, $('.channel-grid-heading'), auxtelDefaultSelected, addToTable)
  addDownloadMetadataButton(meta)
  addToTable(meta, auxtelDefaultSelected, true)
  applyYearControls()
})(jQuery)
