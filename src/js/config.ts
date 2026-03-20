/* Builds the base URL for the application.
 * This is used to construct URLs for API calls and other resources.
 */
function buildHomeUrl() {
  const protocol = window.location.protocol
  const hostname = window.location.host
  const appName = window.location.pathname.split("/")[1]
  return `${protocol}//${hostname}/${appName}/`
}

export const homeUrl = buildHomeUrl()
export const apiUrl = `${homeUrl}api/`
export const imagesUrl = `${homeUrl}static/images/`

// provides a default list of tabs to hide in the night report
export const DEFAULT_HIDDEN_TABS = ["elana"]

// TODO: this should be set in the backend
// See DM-50192
export const hasCCS = (siteLoc: string) => {
  return ["summit", "base", "local"].includes(siteLoc)
}

export const hasFOV = (siteLoc: string) => {
  return ["summit", "usdf-k8s", "local"].includes(siteLoc)
}

export const alwaysSelectedColumns = ["Retrieval fails"]
