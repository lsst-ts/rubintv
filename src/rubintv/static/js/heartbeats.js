import { _getById } from './modules/utils.js'

window.addEventListener('pageshow', function (e) {
  const serviceEls = Array.from(document.querySelectorAll('.service'))

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

  const protocol = this.document.protocol
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
  // use origin to include port
  const hostname = this.document.location.origin.split('//')[1]
  const appName = this.document.location.pathname.split('/')[1]
  const wsUrl = `${wsProtocol}//${hostname}/${appName}/heartbeats_ws`

  const webSocket = new WebSocket(wsUrl)
  webSocket.onmessage = (event) => {
    const heartbeats = JSON.parse(event.data)
    services.forEach(s => {
      const hb = heartbeats[s.id]
      const el = _getById(s.id)

      const hasDependent = s.dependentOn && dependenciesNames.includes(s.dependentOn)
      const depActive = hasDependent ? heartbeats[s.dependentOn].active : true
      const status = hb.active && depActive ? 'active' : 'stopped'

      let msg = `last heartbeat at: ${timestampToDateUTC(hb.curr)} UTC`
      msg = msg.concat(`\nnext check at: ${timestampToDateUTC(hb.next)} UTC`)
      if (!depActive) {
        msg = msg.concat(`\nDependency: ${s.dependentOn} is stopped`)
      }
      el.classList.remove('active', 'stopped')
      el.classList.add(status)
      el.setAttribute('title', msg)
    })
  }

  function timestampToDateUTC (timestamp) {
    // Date takes timestamp in milliseconds
    const d = new Date(timestamp * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
    return d
  }
})
