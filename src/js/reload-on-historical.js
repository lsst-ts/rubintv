import { _getById } from "./modules/utils"
import { WebsocketClient } from "./modules/ws-service-client"
/*
Listens for the status of the historical poller via an event from the websocket
client if the #historicalBusy element shows that historical data for the site
is still loading. Reloads the page once notified that historical data is ready.
*/

window.addEventListener("load", () => {
  if (!window.APP_DATA.historicalBusy) {
    return
  }
  const ws = new WebsocketClient()
  ws.subscribe("historicalStatus")
  window.addEventListener("historicalStatus", (message) => {
    const isBusy = message.detail.data
    if (!isBusy) {
      window.location.reload()
    }
  })
})
