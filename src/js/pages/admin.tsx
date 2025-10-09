import React from "react"
import { createRoot } from "react-dom/client"
import AdminPanels from "../components/AdminPanels"
import HistoricalReset from "../components/HistoricalReset"
import { Menu } from "../components/DropDownMenu"
import { WebsocketClient } from "js/modules/ws-service-client"
;(function () {
  window.addEventListener("DOMContentLoaded", () => {
    const { admin, homeUrl, baseUrl, redisMenus } = window.APP_DATA

    const redisKeyPrefix = (key: string) => {
      const suffix = key.replace(/[^a-zA-Z0-9_]/g, "_").toUpperCase()
      return `RUBINTV_CONTROL_${suffix}`
    }

    const menus: Menu[] = redisMenus as Menu[]

    const ws = new WebsocketClient()
    ws.subscribe("admin")

    const redisEndpointUrl = new URL("api/redis", homeUrl).toString()
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
