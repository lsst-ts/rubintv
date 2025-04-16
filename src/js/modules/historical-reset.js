import { simplePost, _getById, _elWithAttrs } from "./utils"
import { WebsocketClient } from "./ws-service-client"

export function listenForHistoricalReset() {
  const historyResetButton = _getById("historicalReset")
  historyResetButton.addEventListener("click", function (e) {
    e.preventDefault()
    simplePost("api/historical_reset")
      .then(() => {
        historyResetButton.disabled = true
        const notice = _elWithAttrs("h3", {
          text: "Historical data reloading...",
        })
        historyResetButton.after(notice)
        const ws = new WebsocketClient()
        ws.subscribe("historicalStatus")
        window.addEventListener("historicalStatus", (message) => {
          const isBusy = message.detail.data
          if (!isBusy) {
            window.location.reload()
          }
        })
      })
      .catch((err) => {
        console.log(`Couldn't reload historical date: ${err}`)
      })
  })
}
