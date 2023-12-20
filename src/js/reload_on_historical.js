import { _getById } from './modules/utils'
import { WebsocketClient } from './modules/websocket_client'
/*
Listens for the status of the historical poller via an event from the websocket
client if the #historicalBusy element shows that historical data for the site
is still loading. Reloads the page once notified that historical data is ready.
*/

window.addEventListener('load', () => {
  if (_getById('historicalbusy') && _getById('historicalbusy').dataset.historicalbusy !== 'True') {
    return
  }
  const ws = new WebsocketClient()
  ws.subscribe('historicalStatus')
  window.addEventListener('historicalStatus', (message) => {
    const isBusy = message.detail.data
    if (!isBusy) {
      window.location.reload()
    }
  })
})
