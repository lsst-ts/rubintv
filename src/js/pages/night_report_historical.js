import { addTabsListeners, listenForKeypresses } from '../night-report/tabs-ui.js'

window.addEventListener('DOMContentLoaded', () => {
  addTabsListeners()
  listenForKeypresses()
})
