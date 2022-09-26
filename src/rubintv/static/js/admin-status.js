/* global jQuery */
import { ChannelStatus } from './modules/heartbeat.js'

(function ($) {
  const UPDATE_ALL_AFTER = 6000

  const services = Array.from(document.querySelectorAll('.service').values()).map(s => s.id)
  let stats = services.map(s => new ChannelStatus(s))

  setInterval(() => {
    const urlPath = document.location.pathname
    $.get(`${urlPath}/heartbeats`, (newHeartbeats) => {
      console.log('Updating all heartbeats')
      newHeartbeats.forEach(hb => {
        console.log(`Found ${hb.channel}`)
      })
      stats.forEach(service => { service.displayStatus(false) })
      stats = newHeartbeats.map(hb => new ChannelStatus(hb.channel))
    })
  }, UPDATE_ALL_AFTER * 1000)
})(jQuery)
