import { _getById } from '../modules/utils.js'

export function tabsUIInit () {
  const tabs = Array.from(document.querySelectorAll('.tab-title:not(.disabled)'))
  const tabsContent = Array.from(document.querySelectorAll('.tab-content:not(.disabled)'))
  let storedSelected = localStorage.getItem('night-reports-selected')
  if (!storedSelected || tabs.filter((t) => { return t.id.includes(storedSelected) }).length === 0) {
    storedSelected = tabs[0].id.split('tabtitle-')[1]
    localStorage.setItem('night-reports-selected', storedSelected)
  }

  _getById(`tabtitle-${storedSelected}`).classList.add('selected')
  _getById(`tabgroup-${storedSelected}`).classList.add('showing')

  tabs.forEach((tab) => {
    tab.addEventListener('click', (e) => {
      tabs.forEach((t) => { t.classList.remove('selected') })
      tabsContent.forEach((contentBox) => {
        contentBox.classList.remove('showing')
      })
      const clickedTab = e.target
      clickedTab.classList.add('selected')
      const id = clickedTab.id.split('tabtitle-')[1]
      _getById(`tabgroup-${id}`).classList.add('showing')
      localStorage.setItem('night-reports-selected', id)
    })
  })
}
tabsUIInit()

function listenForEfficiency () {
  const keyCode = 'efficiency'
  let keyStore = ''

  document.body.addEventListener('keypress', keyPress)

  function keyPress (e) {
    keyStore = keyStore.concat(e.key)
    if (keyStore === keyCode) {
      Array.from(document.querySelectorAll('#night-reports .disabled')).forEach((el) => {
        el.classList.remove('disabled')
        tabsUIInit()
        document.body.removeEventListener('keypress', keyPress)
      })
    }
    if (keyStore !== keyCode.substring(0, keyStore.length)) {
      keyStore = ''
    }
  }
}
listenForEfficiency()
