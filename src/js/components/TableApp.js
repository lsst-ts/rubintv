import React, { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import TableView, { TableHeader } from './TableView'
import TableControls, { JumpButtons } from './TableControls'
import { _getById, intersect, retrieveSelected } from '../modules/utils'
import { cameraType, channelDataType, metadataType } from './componentPropTypes'

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
    redrawHeaderWidths()
  })

  useEffect(() => {
    window.addEventListener('camera', handleCameraEvent)
    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('camera', handleCameraEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  return (
    <div className="table-container">
      <div className="above-table-sticky">
        <div className="row">
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
        <div className='table-header row'>
          <TableHeader
            camera={camera}
            metadataColumns={selectedMetaCols}
          />
        </div>
        <JumpButtons></JumpButtons>
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
  camera: cameraType,
  /** Date given when first landing on the page. */
  initialDate: PropTypes.string,
  /**  */
  initialChannelData: channelDataType,
  initialMetadata: metadataType
}

function getAllColumnNames (metadataColNames, defaultMetaColNames) {
  return Array.from(new Set(defaultMetaColNames.concat(metadataColNames)))
}

function getAllColumnNamesFromMetadata (metadata) {
  // get the set of all data for list of all available attrs
  const allCols = Object.values(metadata).map(obj => Object.keys(obj)).flat()
  // filter out the indicators (first char is '_')
  return allCols.filter(el => el[0] !== '_')
}

function handleCameraEvent (event) {
  console.debug('TableApp event:', event)
  const { datestamp, data, dataType } = event.detail

  if (datestamp && datestamp !== date) {
    _getById('header-date').textContent = datestamp
    setDate(datestamp)
    setMetadata({})
    setChannelData({})
  }

  if (dataType === 'metadata') {
    setMetadata(data)
  } else if (dataType === 'channelData') {
    setChannelData(data)
  }
}

function getTableColumnWidths () {
  const tRow = document.querySelector('tr')
  const cellsArr = Array.from(tRow.querySelectorAll('td'))
  const cellWidths = cellsArr.map((cell) => { return cell.offsetWidth })
  return cellWidths
}

function redrawHeaderWidths () {
  const columns = getTableColumnWidths()
  const headers = document.querySelectorAll('.grid-title')
  let sum = 0
  headers.forEach((title, ix) => {
    const width = columns[ix]+2
    title.style.left = `${sum}px`
    sum += width
  })
  const sumWidth = `${sum}px`
  document.querySelector('.above-table-sticky').style.width = sumWidth
  document.querySelector('.table-header').style.width = sumWidth
}
