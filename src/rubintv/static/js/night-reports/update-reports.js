import { _getById, getJson, _elWithClass, _elWithAttrs } from '../modules/utils.js'
import { addTabsListeners } from './tabs-ui.js'

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
    Object.keys(newReports.plots).forEach((group) => {
      // add new group to DOM if there's a new one
      if (!Object.keys(prevReports.plots).includes(group)) {
        addNewGroup(group)
        prevReports.plots[group] = []
      }

      // store previous plots for this group by url key
      // and timestamp value
      const prevPlots = prevReports.plots[group].map(
        (/** @type {{ url: string; timestamp: number;}} */ p) => {
          return { [p.url]: p.timestamp }
        }
      )

      const groupEl = _getById(`tabgroup-${group}`)

      newReports.plots[group].forEach(
        (/** @type {{ url: string; timestamp: number; name: string }} */ plot) => {
          // is it a new image?
          if (!Object.keys(prevPlots).includes(plot.url)) {
            const newPlot = createNewPlot(plot)
            groupEl.append(newPlot)
          }
          // is it a new version of a plot?
          // prevReports = { url: timestamp... }
          if (plot.timestamp > prevPlots[plot.url]) {
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
        addNewGroup('Text')
      }
      _getById('tabgroup-text').innerHTML = newReports.text
    }

    prevReports = newReports
    addTabsListeners()
  }

  /**
   * @param {string} group
   */
  function addNewGroup (group) {
    const newTab = _elWithAttrs('div', {
      id: `tabtitle-${group}`,
      class: 'tab-title'
    })
    newTab.textContent = group

    const newGroup = _elWithAttrs('div', {
      id: `tabgroup-${group}`,
      class: 'tab-content plots-grid'
    })

    document.querySelector('.tab-titles').append(newTab)
    document.querySelector('.plots').append(newGroup)
  }

  /**
   * @param {{ url: any; name: string; timestamp: number }} plot
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
   * @param {{ url: string; timestamp: number; }} plot
   */
  function createNewImg (plot) {
    const newImg = document.createElement('img')
    newImg.src = plot.url + '?t=' + plot.timestamp
    newImg.classList.add('report-updated')
    return newImg
  }
})
