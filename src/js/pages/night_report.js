import React from 'react'
import { createRoot } from 'react-dom/client'
import { _getById } from '../modules/utils'
import { WebsocketClient } from '../modules/websocket_client'
import NightReport from '../components/NightReport'
import { addTabsListeners, listenForKeypresses } from '../night-report/tabs-ui'

(function () {
  if (_getById('historicalbusy') &&
   _getById('historicalbusy').dataset.historicalbusy === 'True') {
    return
  }

  const locationName = document.documentElement.dataset.locationname
  const camera = window.APP_DATA.camera || {}
  const nightReport = window.APP_DATA.nightReport || {}
  const date = window.APP_DATA.date || ''
  const baseUrl = window.APP_DATA.baseUrl || ''
  if (!window.APP_DATA.ishistorical) {
    // eslint-disable-next-line no-unused-vars
    const ws = new WebsocketClient('service', 'camera', locationName, camera.name)
  }
  const tableRoot = createRoot(document.getElementById('night-report'))
  tableRoot.render(
    <NightReport
      initialNightReport={nightReport}
      camera={camera}
      locationName={locationName}
      initialDate={date}
      baseUrl={baseUrl}
    />
  )

  window.addEventListener('DOMContentLoaded', () => {
    addTabsListeners()
    listenForKeypresses()
  })
})()
