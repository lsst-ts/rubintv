(() => {
  const display = []
  if (window.location.hostname === 'localhost') {
    display.push('localhost')
  }
  if (window.location.pathname.includes('-dev')) {
    display.push('dev')
  }
  if (display.length > 0) {
    const displayEl = document.createElement('div')
    displayEl.className = 'site-host-display'
    const text = document.createTextNode(display.join(' '))
    displayEl.appendChild(text)
    document.body.append(displayEl)
  }
}).call(this)
