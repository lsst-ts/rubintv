import PropTypes from 'prop-types'
import React, { useState } from 'react'
import Clock from './Clock'
import { _getById } from '../modules/utils'
import { metadataType } from './componentPropTypes'

function TableControls ({ cameraName, allColNames, selected, setSelected, date, metadata }) {
  const [controlsOpen, setControlsOpen] = useState(false)

  const locationName = document.documentElement.dataset.locationname

  const handleCheckboxChange = (name) => {
    setSelected(prevSelected => {
      let updatedSelected
      if (prevSelected.includes(name)) {
        updatedSelected = prevSelected.filter(attr => attr !== name)
      } else {
        updatedSelected = [...prevSelected, name]
      }
      storeSelected(updatedSelected, `${locationName}/${cameraName}`)
      return updatedSelected
    })
  }
  const panelClass = !controlsOpen ? 'table-panel' : 'table-panel open'

  return (
    <>
      <div className={panelClass}>
        <button
          className="table-control-button"
          onClick={() => setControlsOpen(!controlsOpen)}
        >
          Add/Remove Columns
        </button>

        {controlsOpen && (
          <div className="table-controls">
            {allColNames.map(title => (
              <div className="table-control" key={title}>
                <label htmlFor={title}>
                  <input
                    type="checkbox"
                    id={title}
                    name={title}
                    value={1}
                    checked={selected.includes(title)}
                    onChange={() => handleCheckboxChange(title)}
                  />
                  {title}
                </label>
              </div>
            ))}
          </div>
        )}
      </div>
      <DownloadMetadataButton
        date={date}
        cameraName={cameraName}
        metadata={metadata} />
      <Clock />
    </>
  )
}
TableControls.propTypes = {
  /** the names of all metadata columns */
  allColNames: PropTypes.arrayOf(PropTypes.string),
  /** the name of the current camera */
  cameraName: PropTypes.string,
  /** the names of the currently selected columns to display */
  selected: PropTypes.arrayOf(PropTypes.string),
  /** callback function from the parent component TableApp */
  setSelected: PropTypes.func,
  /** the given date */
  date: PropTypes.string,
  /** the current metadata for this camera/date */
  metadata: metadataType
}

export default TableControls

function storeSelected (selected, cameraName) {
  localStorage[cameraName] = JSON.stringify(selected)
}

export function JumpButtons () {
  return (
    <div className='jump-buttons'>
      <button
        onClick={() => _getById('table').scrollIntoView()}
        className='jump-button to-top'
        title='to top'>
        <img src='/rubintv/static/images/jump-arrow.svg'/>
      </button>
      <button
        onClick={() => _getById('table').scrollIntoView(false)}
        className='jump-button to-bottom'
        title='to bottom'>
        <img src='/rubintv/static/images/jump-arrow.svg'/>
      </button>
    </div>
  )
}

function DownloadMetadataButton ({ date, cameraName, metadata }) {
  return (
    <button
      className='button button-small download-metadata'
      onClick={() => downloadMetadata(date, cameraName, metadata)}
    >
      Download Metadata
    </button>
  )
}
DownloadMetadataButton.propTypes = {
  cameraName: PropTypes.string,
  date: PropTypes.string,
  metadata: PropTypes.object
}

function downloadMetadata (date, cameraName, metadata) {
  const a = document.createElement('a')
  const blob = new Blob([JSON.stringify(metadata)])
  const url = window.URL.createObjectURL(blob)
  a.href = url
  a.download = `${cameraName}_${date}.json`
  a.click()
  URL.revokeObjectURL(blob.name)
}
