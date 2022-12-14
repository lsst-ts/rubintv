import { ChannelStatus } from './modules/heartbeat.js'

window.addEventListener('DOMContentLoaded', function () {
  const services = Array.from(document.querySelectorAll('.service')
    .values())
    // eslint-disable-next-line no-new-object
    .map(s => new Object({ id: s.id, dependentOn: s.dataset.dependentOn }))
  const dependenciesNames = Array.from(new Set(services.map(s => s.dependentOn)))
    // eslint-disable-next-line eqeqeq
    .filter(d => !(d === '' || typeof d === 'undefined'))

  const dependencies = Object.fromEntries(
    dependenciesNames.map(d => [d,
      new ChannelStatus(d)])
  )

  services
    .map(s => new ChannelStatus(s.id, dependencies[s.dependentOn]))
})
