import { parseJsonFromDOM } from '../modules/utils.js'
import { TableControls } from '../modules/table-control-grouped.js'
import { drawMeta } from '../modules/draw-grouped-meta.js'
import { applyYearControls } from '../modules/calendar-controls.js'

window.addEventListener('DOMContentLoaded', () => {
  const headers = parseJsonFromDOM('#metadata-headers')
  const meta = parseJsonFromDOM('#table-metadata')
  const tableControls = new TableControls(headers, meta, '.above-table-sticky', drawMeta)
  drawMeta(meta, tableControls.groupedSelected)
  applyYearControls()
})
