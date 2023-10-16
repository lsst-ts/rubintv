import React from 'react'
import { createRoot } from 'react-dom/client'
import TableApp from '../components/TableApp'

const camera = window.APP_DATA.camera || {}
const channelData = window.APP_DATA.tableChannels || {}
const metadata = window.APP_DATA.tableMetadata || {}

const date = window.APP_DATA.date || ''

const tableRoot = createRoot(document.getElementById('channel-day-data'))
tableRoot.render(
  <TableApp camera={camera} date={date} channelData={channelData} metadata={metadata}/>
)
