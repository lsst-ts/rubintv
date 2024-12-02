import ReconnectingWebSocket from "reconnecting-websocket"
import { validate } from "uuid"
import { decodeUnpackWSPayload, getWebSockURL } from "./utils"

// TODO - Simplify this class since subscriptionType is no longer rqrd.
// See DM-46449

export class WebsocketClient {
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
    subscriptionType,
    servicePageType = null,
    location = null,
    camera = null,
    channel = null
  ) {
    const pageID = [location, camera, channel].filter((el) => el).join("/")
    const subscriptionPayload = this.#getSubscriptionPayload(
      subscriptionType,
      servicePageType,
      pageID
    )
    const eventType = this.#getSubscriptionEventType(
      subscriptionType,
      servicePageType
    )

    // Add the subscription to the Map
    this.subscriptions.push(subscriptionPayload)

    if (this.connectionID) {
      this.sendSubscriptionMessages()
    }
  }

  #getSubscriptionPayload(subscriptionType, servicePageType, pageID) {
    let payload
    if (subscriptionType === "historicalStatus") {
      payload = { message: subscriptionType }
    } else {
      const message = [servicePageType, pageID].join(" ")
      payload = { message }
    }
    return payload
  }

  #getSubscriptionEventType(subscriptionType, servicePageType) {
    return subscriptionType === "historicalStatus"
      ? subscriptionType
      : servicePageType
  }

  handleClose(e) {
    console.log("Lost services websocket connection. Retrying")
    this.online = false
    window.dispatchEvent(
      new CustomEvent("ws_status_change", { detail: { online: false } })
    )
  }

  handleOpen(e) {
    this.online = true
    window.dispatchEvent(
      new CustomEvent("ws_status_change", { detail: { online: true } })
    )
  }

  handleMessage(messageEvent) {
    console.debug(messageEvent)
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
    } catch (error) {
      const valid = this.setConnectionID(messageEvent.data)
      if (valid) {
        this.sendSubscriptionMessages()
        return
      } else {
        console.debug("Couldn't parse message:", messageEvent.data)
      }
    }

    if (!data.dataType || !Object.hasOwn(data, "payload")) {
      return
    }

    const detail = {
      dataType: data.dataType,
      data: decodeUnpackWSPayload(data.payload),
      datestamp: data.datestamp,
    }
    window.dispatchEvent(new CustomEvent(data.service, { detail }))
  }

  setConnectionID(messageData) {
    const id = messageData
    if (validate(id)) {
      this.connectionID = id
      console.debug(`Received connection ID: ${id}`)
      return id
    }
    return null
  }

  sendSubscriptionMessages() {
    this.subscriptions.forEach((subscriptionPayload) => {
      const message = {
        ...subscriptionPayload,
        clientID: this.connectionID,
      }
      this.ws.send(JSON.stringify(message))
    })
  }
}
