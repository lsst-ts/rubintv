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
export const imageRoot = `${homeUrl}images/`
