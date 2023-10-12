import ReconnectingWebSocket from 'reconnecting-websocket'

export class WebsocketClient {
  constructor (wsType, pageType = null, location = null, camera = null, channel = null) {
    this.clientID = null
    const pageID = [location, camera, channel].filter((el) => el).join('/')
    this.initMessage = this.#getInitMessage(wsType, pageType, pageID)
    const wsUrl = this.#getURL
    this.wsEvent = this.#getWSEvent(wsType, pageType)
    this.ws = new ReconnectingWebSocket(wsUrl, undefined, { maxRetries: 2 })
    this.ws.onmessage = this.handleMessage.bind(this)
    // this.ws.onopen = this.handleOpen.bind(this)
    // this.ws.onerror = this.handleError.bind(this)
    // this.ws.onclose = this.handleClose.bind(this)
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

  #getURL () {
    const protocol = window.location.protocol
    const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
    const hostname = window.location.host
    const appName = window.location.pathname.split('/')[1]
    return `${wsProtocol}//${hostname}/${appName}/ws/`
  }

  #getWSEvent (wsType, pageType) {
    let eventName
    if (wsType === 'historicalStatus') {
      eventName = wsType
    } else {
      eventName = pageType
    }
    return new Event(eventName, { data: null })
  }

  handleMessage (messageEvent) {
    console.log(messageEvent)
    if (!this.clientID) {
      this.clientID = messageEvent.data
      const clientID = this.clientID
      console.log(`Received client ID: ${clientID}`)
      const message = this.initMessage
      message.clientID = this.clientID
      this.ws.send(JSON.stringify(message))
      return
    }
    const data = JSON.parse(messageEvent.data)
    console.log(data)
    if (!data.dataType || !Object.hasOwn(data, 'payload')) {
      return
    }
    const event = this.wsEvent
    event.data = data.payload
    window.dispatchEvent(event)
  }
}
