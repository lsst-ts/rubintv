import { TableControls } from '../modules/table-control.js'
import { parseJsonFromDOM } from '../modules/utils.js'
import { addToTable } from '../modules/draw-simple-meta.js'
import { applyYearControls } from '../modules/calendar-controls.js'

document.addEventListener('DOMContentLoaded', () => {
  const cameraJson = parseJsonFromDOM('#cameraJson')
  const defaultHeadersAndDescs = cameraJson.metadata_cols
  const meta = parseJsonFromDOM('#table-metadata')
  if (Object.entries(meta).length > 0) {
    const tableControls = new TableControls(
      defaultHeadersAndDescs,
      meta,
      '#table-controls',
      addToTable
    )
    addToTable(meta, tableControls.selected, defaultHeadersAndDescs)
  }
  applyYearControls()
})
