import { parseJsonFromDOM, _getById } from '../modules/utils.js'
import { addToTable } from '../modules/table-startracker.js'
import { starTrackerHeaders } from '../models.js'
import { refreshTableLoop } from '../modules/table-refresher.js'

document.addEventListener('DOMContentLoaded', function () {
  const meta = parseJsonFromDOM('#table-metadata')
  const headers = starTrackerHeaders

  updateTable(meta)
  refreshTableLoop(starTrackerHtmlInject, updateTable, 5)

  function starTrackerHtmlInject (htmlParts) {
    _getById('channel-day-data').innerHTML = htmlParts.table
  }

  function updateTable (meta) {
    addToTable(meta, headers)
  }
})
