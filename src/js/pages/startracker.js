import {
  parseJsonFromDOM,
  _getById
} from '../modules/utils.js'
import { drawMeta } from '../modules/draw-grouped-meta.js'
import { refreshTableLoop } from '../modules/table-refresher.js'
import { TableControls } from '../modules/table-control-grouped.js'

document.addEventListener('DOMContentLoaded', function () {
  const headers = parseJsonFromDOM('#metadata-headers')
  const meta = parseJsonFromDOM('#table-metadata')

  const tableUI = new TableControls(headers, meta, '#table-controls', drawMeta)
  drawMeta(meta, tableUI.groupedSelected)
  refreshTableLoop(starTrackerHtmlInject, updateTable, 5)

  function starTrackerHtmlInject (htmlParts) {
    _getById('channel-day-data').innerHTML = htmlParts.table
  }

  function updateTable (meta) {
    tableUI.draw()
    drawMeta(meta, tableUI.groupedSelected)
  }
})
