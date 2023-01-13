import { ChannelStatus } from './modules/heartbeat.js'

window.addEventListener('load', function () {
  const serviceEls = Array.from(document.querySelectorAll('.service'))
  serviceEls.forEach((el) => {
    el.classList.remove('stopped', 'active')
  })

  const services = serviceEls.map(s => {
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
