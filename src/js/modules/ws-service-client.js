import ReconnectingWebSocket from "reconnecting-websocket"
import { validate } from "uuid"
import { getWebSockURL } from "./utils"

export class WebsocketClient {
  constructor() {
    this.connectionID = null
    this.latestDataBySubscription = new Map() // Store latest data per subscription
    this.ws = new ReconnectingWebSocket(getWebSockURL("ws/data"))
    this.ws.onmessage = this.handleMessage.bind(this)
    this.ws.onclose = this.handleClose.bind(this)
    this.subscriptions = new Map() // To store multiple subscriptions
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
    this.subscriptions.set(eventType, { subscriptionPayload })

    if (this.connectionID) {
      this.sendSubscriptionMessages()
    }
  }

  #getSubscriptionPayload(subscriptionType, servicePageType, pageID) {
    let payload
    if (subscriptionType === "historicalStatus") {
      payload = { messageType: subscriptionType }
    } else {
      const message = [servicePageType, pageID].join(" ")
      payload = { messageType: "service", message }
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
  }

  handleMessage(messageEvent) {
    console.debug(messageEvent)
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

    // Store the latest data for this specific subscription
    const subscription = this.subscriptions.get(data.dataType)
    if (subscription) {
      const detail = {
        dataType: data.dataType,
        data: data.payload,
        datestamp: data.datestamp,
      }
      this.latestDataBySubscription.set(data.dataType, detail) // Store the latest data by subscription type
      window.dispatchEvent(new CustomEvent(data.dataType, { detail }))
    }
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
    for (const { subscriptionPayload } of this.subscriptions.values()) {
      const message = {
        ...subscriptionPayload,
        clientID: this.connectionID,
      }
      this.ws.send(JSON.stringify(message))
    }
  }

  // New method to retrieve the latest detail for a specific subscription
  getLatestDataForSubscription(subscriptionType) {
    return this.latestDataBySubscription.get(subscriptionType) || null
  }
}
