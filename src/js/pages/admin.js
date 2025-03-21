import { listenForHistoricalReset } from "../modules/historical-reset.js"
import React from "react"
import { createRoot } from "react-dom/client"
import AdminPanel from "../components/AdminPanel"
import { simpleGet } from "../modules/utils.js"
;(function () {
  window.addEventListener("DOMContentLoaded", () => {
    listenForHistoricalReset()

    // Only show the admin redis panel on the summit and base sites
    const siteLocation = window.APP_DATA
    if (siteLocation !== "summit" || siteLocation !== "base") {
      return
    }

    const menus = [
      {
        title: "AOS Pipeline",
        key: "RUBINTV_CONTROL_AOS_PIPELINE",
        items: [
          { title: "Danish", value: "danish" },
          { title: "TIE", value: "tie" },
        ],
      },
      {
        title: "Chip selection",
        key: "RUBINTV_CONTROL_CHIP_SELECTION",
        items: [
          { title: "All", value: "all" },
          { title: "Raft checkerboard", value: "raft_checkerboard" },
          { title: "CCD checkerboard", value: "ccd_checkerboard" },
        ],
      },
      {
        title: "Selection strategy",
        key: "RUBINTV_CONTROL_VISIT_PROCESSING_MODE",
        items: [
          { title: "Constant", value: "constant" },
          { title: "Alternating", value: "alternating" },
          { title: "Alternating in twos", value: "alternating_in_twos" },
        ],
      },
    ]

    const redisGetURL = window.APP_DATA.redisGetURL
    console.log("redisGetURL", redisGetURL)
    simpleGet(redisGetURL, { keys: menus.map((menu) => menu.key) }).then(
      (dataStr) => {
        const data = JSON.parse(dataStr)
        menus.forEach((menu) => {
          const value = data[menu.key]
          const item = menu.items.find((item) => item.value === value)
          if (item) {
            menu.selectedItem = item
          }
        })

        adminPanelRoot.render(<AdminPanel menus={menus} />)
      }
    )

    const adminPanel = document.getElementById("admin-panel")
    const adminPanelRoot = createRoot(adminPanel)
    adminPanelRoot.render(<AdminPanel menus={menus} />)
  })
})()
