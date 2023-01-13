import { ChannelStatus } from './modules/heartbeat.js'

window.addEventListener('pageshow', function (e) {
  const serviceEls = Array.from(document.querySelectorAll('.service'))

  if (e.persisted) {
    serviceEls.forEach((el) => {
      el.classList.remove('stopped', 'active')
    })
  }

  serviceEls.map(s => {
    return new ChannelStatus(s.id)
  })
})

window.addEventListener('unload', function () {
  console.log('unloading page...')
  const serviceEls = Array.from(document.querySelectorAll('.service'))
  serviceEls.forEach((el) => {
    el.classList.remove('stopped', 'active')
  })
})
