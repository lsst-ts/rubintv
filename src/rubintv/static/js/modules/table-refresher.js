import { getJson, _getById, parseJsonFromDOM } from './utils.js'

export function refreshTableLoop (injectHTMLCallback, doUpdatingCallback, selected, periodInSecs) {
  setInterval(function () {
    const date = _getById('the-date').dataset.date
    const urlPath = document.location.pathname
    const promise = getJson(urlPath + '/update/' + date)
    promise.then((htmlParts) => {
      injectHTMLCallback(htmlParts)
      const meta = parseJsonFromDOM('#table-metadata')
      if (Object.keys(meta).length !== 0) {
        doUpdatingCallback(meta, selected)
      }
    })
      .catch((e) => {
        console.warn("Couldn't reach server: Unable to refresh table")
      })
  }, periodInSecs * 1000)
}
