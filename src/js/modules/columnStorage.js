import {
  retrieveStoredSelection,
  storeSelected,
  STORAGE_VERSION,
} from "./utils"

export function getStorageKey(locationName, cameraName) {
  return `${locationName}/${cameraName}`
}

export function loadColumnSelection(locationName, cameraName, defaultColumns) {
  const storageKey = getStorageKey(locationName, cameraName)
  const storedColumns = retrieveStoredSelection(storageKey, STORAGE_VERSION)
  const columns = storedColumns || defaultColumns

  // Always ensure storage is initialized
  storeSelected(columns, storageKey, STORAGE_VERSION)

  return columns
}

export function saveColumnSelection(columns, locationName, cameraName) {
  if (!columns?.length) return
  const storageKey = getStorageKey(locationName, cameraName)
  storeSelected(columns, storageKey, STORAGE_VERSION)
}
