import { _getById, getWebSockURL } from "./modules/utils"

window.addEventListener("DOMContentLoaded", () => {
  const display = []
  if (["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    display.push("localhost")
  }
  if (window.location.href.includes("-dev")) {
    display.push("development")
  }
  if (display.length > 0) {
    const displayEl = document.createElement("div")
    displayEl.className = "site-host-display"
    display.forEach((c) => displayEl.classList.add(c))
    const text = document.createTextNode(display.join(" "))
    displayEl.appendChild(text)
    const header = _getById("header-banner")
    header && header.append(displayEl)
  }

  if (!!window.SharedWorker) {
    const heartbeatWorker = new SharedWorker(
      new URL("./modules/heartbeat-worker", import.meta.url)
    )

    const heartbeatWsUrl = getWebSockURL("ws/heartbeats")
    heartbeatWorker.port.postMessage({ heartbeatWsUrl })

    heartbeatWorker.port.onmessage = function (e) {
      console.log("message from worker:", e.data)
    }
  }
})
