import React from "react"
import { createRoot } from "react-dom/client"
import AdminPanels from "../components/AdminPanels"
import HistoricalReset from "../components/HistoricalReset"
import { Menu } from "../components/DropDownMenu"
;(function () {
  window.addEventListener("DOMContentLoaded", () => {
    const { admin, homeUrl, baseUrl } = window.APP_DATA

    const redisKeyPrefix = (key: string) => {
      const suffix = key.replace(/[^a-zA-Z0-9_]/g, "_").toUpperCase()
      return `RUBINTV_CONTROL_${suffix}`
    }
    const redisEndpointUrl = new URL("api/redis", homeUrl).toString()

    const menus: Menu[] = [
      {
        title: "AOS Pipeline",
        key: "RUBINTV_CONTROL_AOS_PIPELINE",
        items: [{ title: "Danish" }, { title: "TIE" }, { title: "AI" }],
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
          { title: "All unvingnetted" },
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

    const authEndpointUrl = new URL(
      "/auth/api/v1/user-info",
      baseUrl
    ).toString()

    const adminPanels = document.getElementById("admin-panels")
    if (adminPanels) {
      const adminPanelsRoot = createRoot(adminPanels)
      adminPanelsRoot.render(
        <>
          <AdminPanels
            initMenus={menus}
            initAdmin={admin}
            redisEndpointUrl={redisEndpointUrl}
            redisKeyPrefix={redisKeyPrefix}
            authEndpointUrl={authEndpointUrl}
          />
          <HistoricalReset />
        </>
      )
    }
  })
})()
