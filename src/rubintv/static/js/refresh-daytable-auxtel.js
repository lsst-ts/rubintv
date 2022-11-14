/* global jQuery */
import { parseJsonFromDOM, createTableControlUI, refreshTable } from './modules/table-control.js'
import { addToTable } from './modules/table-auxtel.js'
import { auxtelDefaultSelected } from './models.js'

(function ($) {
  const selected = auxtelDefaultSelected
  const meta = parseJsonFromDOM('#table-metadata')
  updateTableAndControls(meta, selected)
  refreshTable(injectHTML, updateTableAndControls, selected, 5)

  function injectHTML (htmlParts) {
    $('#per-day-refreshable').html(htmlParts.per_day)
    $('.channel-day-data').html(htmlParts.table)
  }

  function updateTableAndControls (meta, selected) {
    addToTable(meta, selected)
    createTableControlUI(meta, $('#table-controls'), selected, addToTable)
  }
})(jQuery)
