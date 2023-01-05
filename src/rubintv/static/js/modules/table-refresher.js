import { getJson, parseJsonFromDOM } from './utils.js'

export function refreshTableLoop (injectHTMLCallback, doUpdatingCallback, periodInSecs) {
  setInterval(function () {
    const urlPath = document.location.pathname
    const promise = getJson(urlPath + '/update')
    promise.then((htmlParts) => {
      injectHTMLCallback(htmlParts)
      const meta = parseJsonFromDOM('#table-metadata')
      if (Object.keys(meta).length !== 0) {
        doUpdatingCallback(meta)
      }
    })
    promise.catch((e) => {
      console.warn("Couldn't reach server: Unable to refresh table")
    })
  }, periodInSecs * 1000)
}
