/* global jQuery */
import { parseJsonFromDOM, refreshTable } from './modules/table-control.js'
import { addToTable } from './modules/table-startracker.js'
import { starTrackerWideHeaders } from './models.js'

(function ($) {
  const meta = parseJsonFromDOM('#table-metadata')
  const headers = starTrackerWideHeaders
  updateTable(meta, headers)
  refreshTable(starTrackerHtmlInject, updateTable, headers, 5)

  function starTrackerHtmlInject (htmlParts) {
    $('.channel-day-data').html(htmlParts.table)
  }

  function updateTable (meta, headers) {
    addToTable(meta, headers)
  }
})(jQuery)
