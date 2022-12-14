import { ChannelStatus } from './modules/heartbeat.js'

window.addEventListener('DOMContentLoaded', function () {
  const services = Array.from(document.querySelectorAll('.service').values()).map(s => s.id)
  services.map(s => new ChannelStatus(s))
})
