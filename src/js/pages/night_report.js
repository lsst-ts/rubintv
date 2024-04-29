import React from 'react'
import { createRoot } from 'react-dom/client'
import { _getById } from '../modules/utils'
import { WebsocketClient } from '../modules/ws-service-client'
import NightReport from '../components/NightReport'

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
  if (!window.APP_DATA.isHistorical) {
    // eslint-disable-next-line no-unused-vars
    const ws = new WebsocketClient()
    ws.subscribe('service', 'camera', locationName, camera.name)
  }
  const tableRoot = createRoot(_getById('night-report'))
  tableRoot.render(
    <NightReport
      initialNightReport={nightReport}
      camera={camera}
      locationName={locationName}
      initialDate={date}
      baseUrl={baseUrl}
    />
  )
})()
