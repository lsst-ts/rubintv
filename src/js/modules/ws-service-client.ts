import ReconnectingWebSocket from "reconnecting-websocket"
import { validate } from "uuid"
import { decodeUnpackWSPayload, getWebSockURL } from "./utils"

interface WebsocketClientInterface {
  connectionID: string | null
  ws: ReconnectingWebSocket | null
  subscriptions: Array<Record<string, string>>
  online: boolean
  subscribe: (
    servicePageType: string,
    location?: string | null,
    camera?: string | null,
    channel?: string | null
  ) => void
  close: () => void
}

export class WebsocketClient implements WebsocketClientInterface {
  connectionID: string | null
  ws: ReconnectingWebSocket | null
  subscriptions: Array<Record<string, string>>
  online: boolean

  constructor() {
    this.connectionID = null
    this.ws = new ReconnectingWebSocket(getWebSockURL("ws/data"))
    this.ws.onmessage = this.handleMessage.bind(this)
    this.ws.onclose = this.handleClose.bind(this)
    this.ws.onopen = this.handleOpen.bind(this)
    this.subscriptions = [] // To store multiple subscriptions
    this.online = false
  }

  subscribe(
    servicePageType: string,
    location: string | null = null,
    camera: string | null = null,
    channel: string | null = null
  ): void {
    const pageID = [location, camera, channel].filter((el) => el).join("/")
    const subscriptionPayload = this.#getSubscriptionPayload(
      servicePageType,
      pageID
    )

    // Add the subscription to the Map
    this.subscriptions.push(subscriptionPayload)

    if (this.connectionID) {
      this.sendSubscriptionMessages()
    }
  }

  close() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connectionID = null
    this.subscriptions = []
    this.online = false
  }

  #getSubscriptionPayload(
    servicePageType: string,
    pageID: string
  ): Record<string, string> {
    // Create the payload based on the servicePageType and pageID
    let payload
    if (servicePageType === "historicalStatus") {
      payload = { message: servicePageType }
    } else {
      const message = [servicePageType, pageID].join(" ").trim()
      payload = { message }
    }
    return payload
  }

  handleClose() {
    console.log("Lost services websocket connection. Retrying")
    this.online = false
    window.dispatchEvent(
      new CustomEvent("ws_status_change", { detail: { online: false } })
    )
  }

  handleOpen() {
    this.online = true
    window.dispatchEvent(
      new CustomEvent("ws_status_change", { detail: { online: true } })
    )
  }

  handleMessage(messageEvent: MessageEvent) {
    if (!this.online) {
      this.online = true
      window.dispatchEvent(
        new CustomEvent("ws_status_change", { detail: { online: true } })
      )
    }
    if (!this.connectionID) {
      const id = this.setConnectionID(messageEvent.data)
      if (id) {
        this.sendSubscriptionMessages()
        return
      }
    }

    let data
    try {
      data = JSON.parse(messageEvent.data)
    } catch {
      const valid = this.setConnectionID(messageEvent.data)
      if (valid) {
        this.sendSubscriptionMessages()
        return
      } else {
        console.debug("Couldn't parse message:", messageEvent.data)
      }
    }

    if (!data.dataType || !Object.keys(data).includes("payload")) {
      console.warn("Invalid message format:", data)
      return
    }

    const detail = {
      dataType: data.dataType,
      data: decodeUnpackWSPayload(data.payload),
      datestamp: data.datestamp,
    }
    window.dispatchEvent(new CustomEvent(data.service, { detail }))
  }

  setConnectionID(messageData: string): string | null {
    const id = messageData
    if (validate(id)) {
      this.connectionID = id
      console.debug(`Received connection ID: ${id}`)
      return id
    }
    return null
  }

  sendSubscriptionMessages() {
    if (!this.ws || !this.connectionID) {
      console.warn("WebSocket is not connected or connection ID is missing.")
      return
    }
    this.subscriptions.forEach((subscriptionPayload) => {
      const message = {
        ...subscriptionPayload,
        clientID: this.connectionID,
      }
      if (this.ws) {
        this.ws.send(JSON.stringify(message))
      }
    })
  }
}
