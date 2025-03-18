import { listenForHistoricalReset } from "../modules/historical-reset.js"
import React from "react"
import { createRoot } from "react-dom/client"
import AdminPanel from "../components/AdminPanel"
;(function () {
  window.addEventListener("DOMContentLoaded", () => {
    listenForHistoricalReset()
  })
  const adminPanel = document.getElementById("admin-panel")
  createRoot(adminPanel).render(<AdminPanel />)
})()
