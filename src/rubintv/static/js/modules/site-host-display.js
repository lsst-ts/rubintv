(() => {
  const display = []
  if (window.location.hostname === 'localhost') {
    display.push('localhost')
  }
  if (window.location.pathname.includes('-dev')) {
    display.push('development')
  }
  if (display.length > 0) {
    const displayEl = document.createElement('div')
    displayEl.className = 'site-host-display'
    display.forEach((c) => displayEl.classList.add(c))
    const text = document.createTextNode(display.join(' '))
    displayEl.appendChild(text)
    document.body.append(displayEl)
  }
}).call(this)
