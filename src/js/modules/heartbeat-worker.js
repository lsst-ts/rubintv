import ReconnectingWebSocket from "reconnecting-websocket"

let rws
const ports = []

function attachWsListeners(ws) {
  ws.onopen = () => {
    sendToPorts("Connection open")
  }

  ws.onmessage = (event) => {
    sendToPorts(event.data)
  }

  ws.onerror = (error) => {
    console.error("WebSocket error:", error)
  }

  ws.onclose = () => {
    sendToPorts("WebSocket connection closed")
  }

  function sendToPorts(message) {
    ports.forEach((port) => {
      port.postMessage(message)
    })
  }
}

self.onconnect = function (e) {
  const port = e.ports[0]
  ports.push(port)

  port.onmessage = function (e) {
    if (typeof e.data == "object" && "heartbeatWsUrl" in e.data && !rws) {
      const url = e.data.heartbeatWsUrl
      rws = new ReconnectingWebSocket(url, undefined, { maxRetries: 3 })
      attachWsListeners(rws)
    }
  }
}
