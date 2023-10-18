import propTypes from 'prop-types'
import React, { useState } from 'react'
import { _getById } from '../modules/utils'

function TableControls ({ cameraName, allColNames, selected, setSelected, date, metadata }) {
  const [controlsOpen, setControlsOpen] = useState(false)

  const handleCheckboxChange = (name) => {
    setSelected(prevSelected => {
      if (prevSelected.includes(name)) {
        return prevSelected.filter(attr => attr !== name)
      }
      return [...prevSelected, name]
    })
    storeSelected(selected, cameraName)
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
      <JumpButtons />
    </>
  )
}
TableControls.propTypes = {
  allColNames: propTypes.array,
  cameraName: propTypes.string,
  selected: propTypes.array,
  setSelected: propTypes.func,
  date: propTypes.string,
  metadata: propTypes.object
}

export default TableControls

function storeSelected (selected, cameraName) {
  localStorage[cameraName] = JSON.stringify(selected)
}

function JumpButtons () {
  return (
    <div className='jump-buttons'>
      <button
        onClick={() => _getById('channel-day-data').scrollIntoView()}
        className='jump-button to-top'
        title='to top'>
        <img src='/rubintv/static/images/jump-arrow.svg'/>
      </button>
      <button
        onClick={() => _getById('channel-day-data').scrollIntoView(false)}
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
  cameraName: propTypes.string,
  date: propTypes.string,
  metadata: propTypes.object
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

// function orderSelected (metadataColumns, ) {
//   const fromTheDefaults =
//     this.defaultAttrs.filter((/** @type {string} */ attr) =>
//       this.selected.includes(attr))

//   const notInDefaults =
//     this.selected.filter((/** @type {string} */ attr) =>
//       !this.defaultAttrs.includes(attr))

//   this.selected = fromTheDefaults.concat(notInDefaults)
// }

// function addDownloadMetadataButton (cameraName, date, metadata) {
//   const button = _elWithAttrs('button', {
//     class: 'button button-small download-metadata',
//     text: 'Download Metadata'
//   })
//   _getById('table-controls').after(button)
//   button.addEventListener('click', () => {
//     const a = document.createElement('a')
//     const blob = new Blob([JSON.stringify(metadata)])
//     const url = window.URL.createObjectURL(blob)
//     a.href = url
//     a.download = `${cameraName}_${date}.json`
//     a.click()
//     URL.revokeObjectURL(blob.name)
//   })
// }

// function addClickListenerToCopyButtons () {
//   Array.from(document.querySelectorAll('.button.copy')).forEach(button => {
//     button.addEventListener('click', function () {
//       const seq = this.dataset.seq
//       const dateStr = _getById('the-date').dataset.date
//       const dayObs = dateStr.replaceAll('-', '')
//       const dataStr = `dataId = {"day_obs": ${dayObs}, "seq_num": ${seq}, "detector": 0}`
//       navigator.clipboard.writeText(dataStr)
//       const responseMsg = _elWithAttrs('div', { class: 'copied', text: `DataId for ${seq} copied to clipboard` })
//       const pos = this.getBoundingClientRect()
//       responseMsg.setAttribute('style', `top: ${pos.y - (pos.height / 2)}px; left: ${pos.x + (pos.width + 8)}px`)
//       responseMsg.addEventListener('animationend', () => {
//         responseMsg.remove()
//       })
//       document.body.append(responseMsg)
//     })
//   })
// }
