import { ChannelStatus } from './modules/heartbeat.js'

window.addEventListener('popstate', function () {
  console.log('come from back')
  this.window.dispatchEvent('DOMContentLoaded')
})

window.addEventListener('DOMContentLoaded', function () {
  const services = Array.from(document.querySelectorAll('.service'))
    .map(s => {
      return { id: s.id, dependentOn: s.dataset.dependentOn }
    })

  // boil down dependency names
  const dependenciesNames = Array.from(
    new Set(
      services.map(service => { return service.dependentOn })
        // filter out any undefined or empty dependencies
        .filter(serviceName => { return serviceName })
    )
  )

  const dependencies = Object.fromEntries(
    dependenciesNames.map(d => {
      return [d, new ChannelStatus(d)]
    }
    )
  )

  services.map(s => {
    return new ChannelStatus(s.id, dependencies[s.dependentOn])
  })
})
