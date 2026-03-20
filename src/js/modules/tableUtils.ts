import { Camera, Metadata, MetadataColumn } from "../components/componentTypes"

export function getAllColumnNames(
  metadata: Metadata,
  defaultColNames: string[]
) {
  // get the set of all data for list of all available attrs
  const availableColumns = Object.values(metadata)
    .map((obj) => Object.keys(obj))
    .flat()
    .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
  // get the set of all data for list of all available attrs
  const uniqueColNames = Array.from(
    new Set(defaultColNames.concat(availableColumns))
  )
  // filter out the indicators (first char is '_')
  // and the replacement strings for empty channels
  // (first char is '@')
  const filtered = uniqueColNames.filter(
    (el) => !(el[0] === "_" || el[0] === "@")
  )
  return filtered
}

export function getTableColumnWidths() {
  const tRow = document.querySelector("tr")
  if (!tRow) {
    return []
  }
  const cellsArr = Array.from(tRow.querySelectorAll("td"))
  const cellWidths = cellsArr.map((cell) => {
    return cell.offsetWidth
  })
  return cellWidths
}

/**
 * Redraws the header widths based on the current table column widths.
 */
export function redrawHeaderWidths() {
  const columns = getTableColumnWidths()
  const headers = Array.from(document.querySelectorAll(".grid-title"))
  if (columns.length !== headers.length) {
    return false
  }
  let sum = 0
  for (let ix = 0; ix < headers.length; ix++) {
    const title = headers[ix] as HTMLElement
    const width = columns[ix] + 2
    title.style.left = `${sum}px`
    sum += width
  }
  if (sum > 0) {
    const sumWidth = `${Math.ceil(sum) + 2}px`
    const aboveTable = document.querySelector(
      ".above-table-sticky"
    ) as HTMLElement
    const tableHeader = document.querySelector(".table-header") as HTMLElement
    if (aboveTable) {
      aboveTable.style.width = sumWidth
    }
    if (tableHeader) {
      tableHeader.style.width = sumWidth
    }
    return true
  }
  return false
}

// Column configuration derived from camera metadata
export function getDefaultColumns(camera: Camera) {
  return camera.metadata_columns
    ? Object.entries(camera.metadata_columns).map(
        ([name, desc]) =>
          ({
            name,
            desc,
          }) as MetadataColumn
      )
    : []
}
