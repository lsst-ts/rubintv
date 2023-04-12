import { getJson, parseJsonFromDOM } from './utils.js'

/**
 * @param {{ (htmlParts: any): void; }} injectHTMLCallback
 * @param {{ (meta: any): void; }} doUpdatingCallback
 * @param {number} periodInSecs
 */
export function refreshTableLoop (injectHTMLCallback, doUpdatingCallback, periodInSecs) {
  setInterval(function () {
    const urlPath = document.location.pathname
    const promise = getJson(urlPath + '/update')
    promise.then((htmlParts) => {
      injectHTMLCallback(htmlParts)
      const meta = parseJsonFromDOM('#table-metadata')
      doUpdatingCallback(meta)
    })
    promise.catch((e) => {
      console.warn("Couldn't reach server: Unable to refresh table")
    })
  }, periodInSecs * 1000)
}
