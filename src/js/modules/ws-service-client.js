import ReconnectingWebSocket from 'reconnecting-websocket'
import { validate } from 'uuid'
import { getWebSockURL } from './utils'

export class WebsocketClient {
  // wsType is either 'historicalStatus' or 'service'
  // pageType for 'service's are either 'camera', 'channel' or 'nightreport'
  constructor () {
    this.clientID = null
    this.ws = new ReconnectingWebSocket(getWebSockURL('ws'))
    this.ws.onmessage = this.handleMessage.bind(this)
    this.ws.onclose = this.handleClose.bind(this)
  }

  subscribe (wsType, pageType = null, location = null, camera = null, channel = null) {
    const pageID = [location, camera, channel].filter((el) => el).join('/')
    this.initMessage = this.#getInitMessage(wsType, pageType, pageID)
    this.wsEventName = this.#getWSEventName(wsType, pageType)
    // If clientID exists, send the initial message to subscribe to the new service
    if (this.clientID) {
      this.sendInitialMessage()
    }
  }

  #getInitMessage (wsType, pageType, pageID) {
    let messageJson
    if (wsType === 'historicalStatus') {
      messageJson = { messageType: wsType }
    } else {
      const message = [pageType, pageID].join(' ')
      messageJson = { messageType: 'service', message }
    }
    return messageJson
  }

  #getWSEventName (wsType, pageType) {
    let eventName
    if (wsType === 'historicalStatus') {
      eventName = wsType
    } else {
      eventName = pageType
    }
    return eventName
  }

  handleClose (e) {
    console.log('Lost services websocket connection. Retrying')
  }

  handleMessage (messageEvent) {
    console.debug(messageEvent)
    if (!this.clientID) {
      const id = this.setClientID(messageEvent.data)
      if (id) {
        this.sendInitialMessage()
        return
      }
    }
    let data
    try {
      data = JSON.parse(messageEvent.data)
      // if the connection closes in the meantime
      // the server might send a new client ID
      // so catch this in case
    } catch (error) {
      const valid = this.setClientID(messageEvent.data)
      if (valid) {
        this.sendInitialMessage()
        return
      } else {
        console.debug('Couldn\'t parse message:', messageEvent.data)
      }
    }
    if (!data.dataType || !Object.hasOwn(data, 'payload')) {
      return
    }
    const detail = {
      dataType: data.dataType,
      data: data.payload,
      datestamp: data.datestamp
    }
    window.dispatchEvent(new CustomEvent(this.wsEventName, { detail }))
  }

  setClientID (messageData) {
    const id = messageData
    if (validate(id)) {
      this.clientID = id
      console.debug(`Received client ID: ${id}`)
      return id
    }
    return null
  }

  sendInitialMessage () {
    const message = this.initMessage
    message.clientID = this.clientID
    this.ws.send(JSON.stringify(message))
  }
}
