import { getJson, _getById, parseJsonFromDOM } from './utils.js'

export function refreshTableLoop (injectHTMLCallback, doUpdatingCallback, selected, periodInSecs) {
  setInterval(function () {
    const date = _getById('the-date').dataset.date
    const urlPath = document.location.pathname
    getJson(urlPath + '/update/' + date)
      .then((htmlParts) => {
        injectHTMLCallback(htmlParts)
        const meta = parseJsonFromDOM('#table-metadata')
        if (Object.keys(meta).length !== 0) {
          doUpdatingCallback(meta, selected)
        }
      })
      .catch(() => {
        console.log("Couldn't reach server")
      })
  }, periodInSecs * 1000)
}
