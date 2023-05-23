import {
  parseJsonFromDOM,
  _getById
} from '../modules/utils.js'
import { drawTable } from '../modules/draw-grouped-table.js'
import { refreshTableLoop } from '../modules/table-refresher.js'
import { TableControls } from '../modules/table-control-grouped.js'

document.addEventListener('DOMContentLoaded', function () {
  const headers = parseJsonFromDOM('#metadata-headers')
  const meta = parseJsonFromDOM('#table-metadata')

  const tableUI = new TableControls(headers, meta, '#table-controls', drawTable)
  drawTable(meta, tableUI.groupedSelected)
  refreshTableLoop(starTrackerHtmlInject, updateTable, 5)

  function starTrackerHtmlInject (htmlParts) {
    _getById('channel-day-data').innerHTML = htmlParts.table
  }

  function updateTable (meta) {
    tableUI.draw()
    drawTable(meta, tableUI.groupedSelected)
  }
})
