import { _getById } from './modules/utils.js'
import { ReconnectingWebSocket } from './modules/reconnecting-websocket.js'

window.addEventListener('pageshow', function (e) {
  const location = _getById('location').dataset.location

  // scrape relevent services from page
  const serviceEls = Array.from(document.querySelectorAll('.service'))
  const services = serviceEls.map(s => {
    return { id: s.id, el: s, dependentOn: s.dataset.dependentOn }
  })

  // boil down dependency names
  const dependenciesNames = Array.from(
    new Set(
      services.map(service => { return service.dependentOn })
        // filter out any undefined or empty dependencies
        .filter(serviceName => { return serviceName })
    )
  )

  // init websocket listener
  const protocol = this.document.location.protocol
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
  // use origin to include port
  const hostname = this.document.location.origin.split('//')[1]
  const appName = this.document.location.pathname.split('/')[1]
  const wsUrl = `${wsProtocol}//${hostname}/${appName}/${location}/heartbeats_ws`

  const rws = new ReconnectingWebSocket(wsUrl)

  rws.onopen = () => {
    console.log('Listening for heartbeats...')
  }

  rws.onmessage = heartbeatHandler

  function heartbeatHandler (event) {
    const heartbeats = JSON.parse(event.data)
    services.forEach(s => {
      const hb = heartbeats[s.id]
      if (!hb) return
      const hasDependent = s.dependentOn && dependenciesNames.includes(s.dependentOn)
      const depActive = hasDependent ? heartbeats[s.dependentOn].active : true
      const status = hb.active && depActive ? 'active' : 'stopped'

      let msg = `last heartbeat at: ${timestampToDateUTC(hb.curr)} UTC`
      msg = msg.concat(`\nnext check at: ${timestampToDateUTC(hb.next)} UTC`)
      if (!depActive) {
        msg = msg.concat(`\nDependency: ${s.dependentOn} is stopped`)
      }

      s.el.classList.remove('active', 'stopped')
      s.el.classList.add(status)
      s.el.setAttribute('title', msg)
    })
  }

  rws.onclose = () => {
    console.log('Heartbeats websocket closed')
  }

  function timestampToDateUTC (timestamp) {
    // Date takes timestamp in milliseconds
    const d = new Date(timestamp * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
    return d
  }
})
