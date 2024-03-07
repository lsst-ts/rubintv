import ReconnectingWebSocket from "reconnecting-websocket"
import { getURL } from "./websocket_client"

onconnect = function(event) {
  const port = event.port[0]

  const URL = getURL('heartbeats')
  const ws = new ReconnectingWebSocket(URL)

  // ws.onopen =

  port.onmessage = function(e) {
    console.log(e.data)
    port.postMessage('recvd message from server')
  }
}
