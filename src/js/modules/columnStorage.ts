import {
  retrieveStoredSelection,
  storeSelected,
  STORAGE_VERSION,
} from "./utils"

export function getStorageKey(locationName: string, cameraName: string) {
  return `${locationName}/${cameraName}`
}

export function loadColumnSelection(
  locationName: string,
  cameraName: string,
  defaultColumns: string[]
) {
  const storageKey = getStorageKey(locationName, cameraName)
  const storedColumns = retrieveStoredSelection(storageKey, STORAGE_VERSION)
  const columns = storedColumns || defaultColumns

  // Always ensure storage is initialized
  storeSelected(columns, storageKey, STORAGE_VERSION)

  return columns
}

export function saveColumnSelection(
  columns: string[],
  locationName: string,
  cameraName: string
) {
  if (!columns?.length) return
  const storageKey = getStorageKey(locationName, cameraName)
  storeSelected(columns, storageKey, STORAGE_VERSION)
}
