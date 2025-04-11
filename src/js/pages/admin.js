import { listenForHistoricalReset } from "../modules/historical-reset.js"
import React from "react"
import { createRoot } from "react-dom/client"
import AdminPanel from "../components/AdminPanel"
import { simpleGet } from "../modules/utils.js"
;(function () {
  window.addEventListener("DOMContentLoaded", () => {
    listenForHistoricalReset()

    const { redisGetURL, admin, baseURL } = window.APP_DATA

    const menus = [
      {
        title: "AOS Pipeline",
        key: "RUBINTV_CONTROL_AOS_PIPELINE",
        items: [{ title: "Danish" }, { title: "TIE" }],
      },
      {
        title: "Chip selection",
        key: "RUBINTV_CONTROL_CHIP_SELECTION",
        items: [
          { title: "All" },
          { title: "Raft checkerboard" },
          { title: "CCD checkerboard" },
          { title: "5-on-a-die" },
          { title: "Minimal" },
          { title: "Ultra-minimal" },
        ],
      },
      {
        title: "Selection strategy",
        key: "RUBINTV_CONTROL_VISIT_PROCESSING_MODE",
        items: [
          { title: "Constant" },
          { title: "Alternating" },
          { title: "Alternating in twos" },
        ],
      },
    ]

    // add a value to each menu item
    // which is the title in lowercase and with spaces replaced by underscores
    menus.forEach((menu) => {
      menu.items.forEach((item) => {
        item.value = item.title.toLowerCase().replace(/ /g, "_")
      })
    })

    // get already selected values if set
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

        adminPanelRoot.render(<AdminPanel menus={menus} admin={admin} />)
      }
    )

    const auth_api_url = new URL("/auth/api/v1/user-info", baseURL)
    simpleGet(auth_api_url).then((dataStr) => {
      try {
        // check if the response is a valid JSON
        JSON.parse(dataStr)
      } catch (e) {
        console.error("Error parsing auth api JSON response:", e)
        return
      }
      const data = JSON.parse(dataStr)
      // check if the username is the same as the admin username
      if (data.username !== admin) {
        console.error(`User ${data.username} is not the admin user ${admin}.`)
      }
      admin.email = data.email
      admin.name = data.name
      adminPanelRoot.render(<AdminPanel menus={menus} admin={admin} />)
    })

    const adminPanel = document.getElementById("admin-panel")
    const adminPanelRoot = createRoot(adminPanel)
    adminPanelRoot.render(<AdminPanel menus={menus} admin={admin} />)
  })
})()
