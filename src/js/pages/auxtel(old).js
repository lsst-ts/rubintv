import { TableControls } from '../modules/table-control.js'
import { addToTable } from '../modules/draw-simple-meta.js'
import { WebsocketClient } from '../modules/websocket_client.js'

window.addEventListener('load', function () {
  const camera = this.window.APP_DATA.camera
  // const channels = this.window.APP_DATA.table_channels
  const meta = this.window.APP_DATA.table_metadata
  const defaultColumns = camera.metadata_cols
  const location = this.document.documentElement.dataset.location
  const cameraName = camera.name

  if (Object.entries(meta).length > 0) {
    const tableControls = new TableControls(
      defaultColumns,
      meta,
      '#table-controls',
      addToTable
    )
    addToTable(meta, tableControls.selected, defaultColumns)

    // eslint-disable-next-line no-unused-vars
    const ws = new WebsocketClient('service', 'camera', location, cameraName)
    this.window.addEventListener('camera', (message) => {
      console.log(message.data)
    })
  }
})
