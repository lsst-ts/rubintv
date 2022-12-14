import { parseJsonFromDOM, _getById } from '../modules/utils.js'
import { addToTable } from '../modules/table-startracker.js'
import { starTrackerWideHeaders } from '../models.js'
import { refreshTableLoop } from '../modules/table-refresher.js'

window.addEventListener('DOMContentLoaded', function () {
  const meta = parseJsonFromDOM('#table-metadata')
  const headers = starTrackerWideHeaders

  updateTable(meta, headers)
  refreshTableLoop(starTrackerHtmlInject, updateTable, headers, 5)

  function starTrackerHtmlInject (htmlParts) {
    _getById('channel-day-data').innerHTML = htmlParts.table
  }

  function updateTable (meta, headers) {
    addToTable(meta, headers)
  }
})
