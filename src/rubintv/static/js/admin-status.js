/* global jQuery */
import { ChannelStatus } from './modules/heartbeat.js'

(function ($) {
  const services = Array.from(document.querySelectorAll('.service').values()).map(s => s.id)
  services.map(s => new ChannelStatus(s))
})(jQuery)
