import { _getById, getJson, _elWithClass, _elWithAttrs } from '../modules/utils.js'
import { addTabsListeners, listenForKeypresses } from '../night-report/tabs-ui.js'

window.addEventListener('DOMContentLoaded', function () {
  let prevReports = JSON.parse(_getById('reports-json').textContent)

  setInterval(updateEvents, 5000)
  function updateEvents () {
    const theDate = _getById('the-date').dataset.date
    const url = window.location + '/update/' + theDate
    getJson(url)
      .then(success)
      .catch((reason) => {
        // suppress network errors
        // console.warn(reason)
      })
  }

  /**
   * @param {{ plots: { [x: string]: any[]; }; text: string; }} newReports
   */
  function success (newReports) {
    // update plots - plots object will always exist
    Object.keys(newReports.plots).forEach(group => {
      // add new group to DOM if there's a new one
      if (!Object.keys(prevReports.plots).includes(group)) {
        addNewGroupGUI(group)
        prevReports.plots[group] = {}
      }

      // store previous plots for this group by url key
      // and hash value
      const prevPlots = {}
      Object.keys(prevReports.plots[group]).forEach(
        pName => {
          const p = prevReports.plots[group][pName]
          prevPlots[p.url] = p.hash
        }
      )
      const groupEl = _getById(`tabgroup-${group.toLowerCase()}`)

      Object.keys(newReports.plots[group]).forEach(
        plotName => {
          const plot = newReports.plots[group][plotName]
          // is it a new image?
          console.log(Object.keys(prevPlots).includes(plot.url))
          if (!Object.keys(prevPlots).includes(plot.url)) {
            const newPlot = createNewPlot(plot)
            groupEl.append(newPlot)
          }
          // is it a different version of a plot?
          // prevReports = { url: hash... }
          if (plot.hash !== prevPlots[plot.url]) {
            const oldImg = document.querySelector(`img[src^="${plot.url}"]`)
            const newImg = createNewImg(plot)
            newImg.addEventListener('load', (e) => {
              oldImg.replaceWith(newImg)
            })
          }
        }
      )
    })
    // update text
    if (newReports.text) {
      if (!prevReports.text) {
        addNewGroupGUI('Text')
      }
      const textEl = _getById('tabgroup-text')
      const textClasses = textEl.classList.value
      textEl.outerHTML = newReports.text
      textEl.classList.value = textClasses
    }
    prevReports = newReports
    addTabsListeners()
    listenForKeypresses()
  }

  /**
   * @param {string} group
   */
  function addNewGroupGUI (group) {
    const newTab = _elWithAttrs('div', {
      id: `tabtitle-${group.toLowerCase()}`,
      class: 'tab-title'
    })
    newTab.textContent = group

    const newGroup = _elWithAttrs('div', {
      id: `tabgroup-${group.toLowerCase()}`,
      class: 'tab-content plots-grid'
    })

    document.querySelector('.tab-titles').append(newTab)
    document.querySelector('.plots').append(newGroup)
  }

  /**
   * @param {{ url: any; name: string; hash: string }} plot
   */
  function createNewPlot (plot) {
    const newPlot = _elWithClass('figure', 'plot')
    const link = (_elWithAttrs('a', { href: plot.url }))
    const img = createNewImg(plot)
    const title = _elWithAttrs('figcaption')
    title.textContent = plot.name
    link.append(img)
    newPlot.append(link, title)
    return newPlot
  }

  /**
   * @param {{ url: string; hash: string; }} plot
   */
  function createNewImg (plot) {
    const newImg = document.createElement('img')
    newImg.src = plot.url + '?t=' + plot.hash
    newImg.classList.add('report-updated')
    return newImg
  }
})
