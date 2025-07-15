import ReconnectingWebSocket from "reconnecting-websocket"

let rws: ReconnectingWebSocket | null = null
const ports: MessagePort[] = []

function attachWsListeners(ws: ReconnectingWebSocket): void {
  ws.onopen = (): void => {
    sendToPorts("Connection open")
  }

  ws.onmessage = (event: MessageEvent): void => {
    sendToPorts(event.data)
  }

  ws.onerror = (error): void => {
    console.error("WebSocket error:", error)
  }

  ws.onclose = (): void => {
    sendToPorts("WebSocket connection closed")
  }

  function sendToPorts(message: unknown): void {
    ports.forEach((port: MessagePort) => {
      port.postMessage(message)
    })
  }
}

// Declare SharedWorkerGlobalScope if not available in TypeScript's DOM typings
declare const SharedWorkerGlobalScope: {
  prototype: SharedWorkerGlobalScope
  new (): SharedWorkerGlobalScope
}

interface SharedWorkerGlobalScope extends Worker {
  onconnect: ((this: SharedWorkerGlobalScope, ev: MessageEvent) => void) | null
}

;(self as unknown as SharedWorkerGlobalScope).onconnect = function (
  e: MessageEvent
) {
  const port = e.ports[0]
  ports.push(port)

  port.onmessage = function (e: MessageEvent) {
    if (typeof e.data == "object" && "heartbeatWsUrl" in e.data && !rws) {
      const url = e.data.heartbeatWsUrl
      rws = new ReconnectingWebSocket(url, undefined, { maxRetries: 3 })
      attachWsListeners(rws)
    }
  }
}
