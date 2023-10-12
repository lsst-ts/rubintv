import { TableControls } from '../modules/table-control.js'
import { parseJsonFromDOM } from '../modules/utils.js'
import { addToTable } from '../modules/draw-simple-meta.js'
// import { initWebSocketClient } from '../modules/websocket_client.js'

window.addEventListener('load', function () {
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

  // const location = this.document.documentElement.dataset.location
  // const camera = cameraJson.name
  // let serviceConnected = false
  // initWebSocketClient('/')
  // ws.onopen = () => {
  //   const req = `camera ${location}/${camera}`
  //   console.log(`sending: ${req}`)
  //   ws.send(req)
  // }
  // ws.onmessage = (message) => {
  //   const res = message.data
  //   if (serviceConnected) {
  //     const data = JSON.parse(res)
  //     consumeWSData(data)
  //   }
  //   if (res === `OK/${location}/${camera}`) {
  //     console.log(res)
  //     serviceConnected = true
  //   }
  // }

  // function consumeWSData (data) {
  //   console.log(data)
  // }
})
