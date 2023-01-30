import { _getById } from '../modules/utils.js'

export function tabsUIInit () {
  const tabs = Array.from(document.getElementsByClassName('tab-title'))
  const tabsContent = Array.from(document.getElementsByClassName('tab-content'))
  let storedSelected = localStorage.getItem('night-reports-selected')
  if (!storedSelected) {
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
