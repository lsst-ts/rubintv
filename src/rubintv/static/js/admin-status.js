/* global jQuery */
import { ChannelStatus } from './modules/heartbeat.js'

(function ($) {
  const UPDATE_ALL_AFTER = 6000

  const heartbeatsText = document.querySelector('#heartbeats').text
  const heartbeats = JSON.parse(heartbeatsText)
  let statuses = heartbeats.map(hb => new ChannelStatus(hb))

  setInterval(() => {
    const urlPath = document.location.pathname
    $.get(`${urlPath}/heartbeats`, (newHeartbeats) => {
      console.log('Updating all heartbeats')
      newHeartbeats.forEach(hb => {
        console.log(`Found ${hb.channel}`)
      })
      statuses.forEach(hb => { hb.displayStatus(false) })
      statuses = newHeartbeats.map(hb => new ChannelStatus(hb))
    })
  }, UPDATE_ALL_AFTER * 1000)
})(jQuery)
