import React from 'react'
import { createRoot } from 'react-dom/client'
import TableApp from '../components/TableApp'
import { _getById } from '../modules/utils'

(function () {
  if (_getById('historicalbusy') &&
   _getById('historicalbusy').dataset.historicalbusy === 'True') {
    return
  }

  const camera = window.APP_DATA.camera || {}
  const channelData = window.APP_DATA.tableChannels || {}
  const metadata = window.APP_DATA.tableMetadata || {}

  const date = window.APP_DATA.date || ''

  const tableRoot = createRoot(document.getElementById('table'))
  tableRoot.render(
    <TableApp
      camera={camera}
      initialDate={date}
      initialChannelData={channelData}
      initialMetadata={metadata}
    />
  )
})()
