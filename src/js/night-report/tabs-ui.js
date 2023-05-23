import { _getById } from '../modules/utils.js'

export function addTabsListeners () {
  const tabs = Array.from(document.querySelectorAll('.tab-title:not(.disabled)'))
  if (tabs.length === 0) return

  const tabsContent = document.querySelectorAll('.tab-content:not(.disabled)')

  let storedSelected = localStorage.getItem('night-report-selected')
  if (!storedSelected || tabs.filter((t) => { return t.id.includes(storedSelected) }).length === 0) {
    storedSelected = tabs[0].id.split('tabtitle-')[1]
    localStorage.setItem('night-report-selected', storedSelected)
  }

  const id = storedSelected.toLowerCase()
  _getById(`tabtitle-${id}`).classList.add('selected')
  _getById(`tabgroup-${id}`).classList.add('showing')

  tabs.forEach((tab) => {
    tab.addEventListener('click', (e) => {
      tabs.forEach((t) => { t.classList.remove('selected') })
      tabsContent.forEach((contentBox) => {
        contentBox.classList.remove('showing')
      })
      const clickedTab = e.target
      // The following two lines ignore typing as lint complains
      // that an EventTarget object doesn't have `classList` and `id`
      // properties but the EventTarget returned here will always be
      // an HTMLElement, which has both.
      // @ts-ignore
      clickedTab.classList.add('selected')
      // @ts-ignore
      const id = clickedTab.id.split('tabtitle-')[1]
      _getById(`tabgroup-${id.toLowerCase()}`).classList.add('showing')
      localStorage.setItem('night-report-selected', id)
    })
  })
}
addTabsListeners()

export function listenForKeypresses () {
  const keysAndTabs = { efficiency: 'text', elana: 'elana' }
  let keyCodes = Object.keys(keysAndTabs)
  let typed = ''

  document.body.addEventListener('keypress', keyPress)

  /**
   * @param {{ key: string; }} e
   */
  function keyPress (e) {
    typed = typed.concat(e.key)
    // has the whole key been typed out?
    if (keyCodes.includes(typed)) {
      // reveal the tab
      console.log(`added ${typed}`)
      const tabToReveal = keysAndTabs[typed]
      document.querySelectorAll(`[id$="-${tabToReveal}"]`).forEach((el) => {
        el.classList.remove('disabled')
        addTabsListeners()
      })
      // remove the key from the active array
      keyCodes = keyCodes.filter(k => { return k !== typed })
      // remove the listener altogether if no more keys left
      if (keyCodes.length === 0) {
        document.body.removeEventListener('keypress', keyPress)
      }
    }
    // check to see if any of the keys is being typed out
    const isTypingAnyKey = keyCodes.map(k => {
      return typed === k.substring(0, typed.length)
    })
    if (isTypingAnyKey.reduce(
      (acc, curr) => acc || curr, false) === false) {
      typed = ''
    }
  }
}
