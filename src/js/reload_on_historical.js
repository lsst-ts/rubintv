import { initWebSocketClient } from './modules/utils.js'
/*
Listens for the status of the historical poller via websocket.
If it's not busy, all is well and the connection is closed.
If it is busy but we haven't been notified before, make a note of the
busy-ness.
If it's been busy before and now it's not, reload the page and close the
connection.
This can re-run safely when the page is reloaded.
*/

const socket = initWebSocketClient('/status')

let hasBeenBusy = null
socket.onmessage = (message) => {
  const data = JSON.parse(message.data)
  if (Object.hasOwn(data, 'historicalBusy')) {
    const isBusy = data.historicalBusy
    if (!isBusy && hasBeenBusy) {
      window.location.reload()
      socket.close()
    } else if (!isBusy) {
      socket.close()
    } else {
      hasBeenBusy = true
    }
  }
}
socket.onopen = () => {
  console.log('Listening for historical status...')
}
socket.onclose = () => {
  console.log('Status websocket closed')
}
