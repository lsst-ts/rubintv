import React, { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import TableView from './TableView'
import TableControls from './TableControls'
import { _getById, intersect } from '../modules/utils'

export default function TableApp ({ camera, initialDate, initialChannelData, initialMetadata }) {
  const [date, setDate] = useState(initialDate)
  const [channelData, setChannelData] = useState(initialChannelData)
  const [metadata, setMetadata] = useState(initialMetadata)

  const locationName = document.documentElement.dataset.locationname

  // convert metadata_cols into array of objects if they exist
  let defaultCols
  if (camera.metadata_cols) {
    defaultCols = Object.entries(camera.metadata_cols)
      .map(([name, desc]) => { return { name, desc } })
  } else {
    defaultCols = []
  }
  const defaultColNames = defaultCols.map(col => col.name)
  const metaColNames = getAllColumnNamesFromMetadata(metadata)
  const allColNames = getAllColumnNames(metaColNames, defaultColNames)

  const [selected, setSelected] = useState(
    () => {
      const savedColumns = retrieveSelected(`${locationName}/${camera.name}`)
      if (savedColumns) {
        const intersectedColumns = intersect(savedColumns, allColNames)
        return intersectedColumns
      }
      return defaultColNames
    }
  )

  const selectedObjs = selected.map(c => { return { name: c } })
  const selectedMetaCols = defaultCols.filter(c => selected.includes(c.name))
    .concat(selectedObjs.filter(o => !defaultColNames.includes(o.name)))

  useEffect(() => {
    function handleCameraEvent (event) {
      console.debug('TableApp event:', event)
      const { datestamp, data, dataType } = event.detail

      if (datestamp && datestamp !== date) {
        _getById('header-date').textContent = datestamp
        setDate(datestamp)
      }

      if (dataType === 'metadata') {
        setMetadata(data)
      } else if (dataType === 'channelData') {
        setChannelData(data)
      }
    }
    window.addEventListener('camera', handleCameraEvent)

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('camera', handleCameraEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  return (
    <div className="table-container">
      <div className="above-table-sticky">
        <h3 id="the-date">Data for day: <span className="date">{date}</span></h3>
        <TableControls
          cameraName={camera.name}
          allColNames={allColNames}
          selected={selected}
          setSelected={setSelected}
          date={date}
          metadata={metadata}
        />
      </div>
        <TableView
          camera={camera}
          channelData={channelData}
          metadata={metadata}
          metadataColumns={selectedMetaCols}
          />
    </div>
  )
}
TableApp.propTypes = {
  camera: PropTypes.object,
  initialDate: PropTypes.string,
  initialChannelData: PropTypes.object,
  initialMetadata: PropTypes.object
}

function retrieveSelected (cameraName) {
  const retrieved = localStorage.getItem(cameraName)
  return (retrieved && JSON.parse(retrieved))
}

/**
 * @param {{ [s: string]: any }} metadata
 */
function getAllColumnNames (metadataColNames, defaultMetaColNames) {
  return Array.from(new Set(defaultMetaColNames.concat(metadataColNames)))
}

function getAllColumnNamesFromMetadata (metadata) {
  // get the set of all data for list of all available attrs
  const allCols = Object.values(metadata).map(obj => Object.keys(obj)).flat()
  // filter out the indicators (first char is '_')
  return allCols.filter(el => el[0] !== '_')
}
