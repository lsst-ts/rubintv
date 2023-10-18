import React, { useState } from 'react'
import propTypes from 'prop-types'
import SimpleTableView from './SimpleTableView'
import TableControls from './TableControls'
import { intersect } from '../modules/utils'

export default function TableApp ({ camera, date, channelData, metadata }) {
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
      const savedColumns = retrieveSelected(camera.name)
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
        <SimpleTableView
          camera={camera}
          channelData={channelData}
          metadata={metadata}
          metadataColumns={selectedMetaCols}
          />
    </div>
  )
}
TableApp.propTypes = {
  camera: propTypes.object,
  date: propTypes.string,
  channelData: propTypes.object,
  metadata: propTypes.object
}

function retrieveSelected (cameraName) {
  const retrieved = localStorage[cameraName]
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
