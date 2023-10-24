import React, { useState, useEffect } from 'react'
import propTypes from 'prop-types'

function NightReportText ({ nightReport }) {
  const texts = nightReport.text || {}
  return (
    <div id='tabgroup-text' className='dashboard tab-content'>
      {Object.entries(texts).map(([textName, text]) => {
        if (textName.startsWith('text_')) {
          // for multiline text
          if (texts[textName]) {
            return (
              <ul className='dashboard-text' key={textName}>
                <li>
                {texts[textName].split('\n').map((line, lineNum) => {
                  if (line) {
                    return (
                        <p key={lineNum}>{line.replace('  ', String.fromCharCode(160) + String.fromCharCode(160))}</p>
                    )
                  } else {
                    return <br key={lineNum}/>
                  }
                })}
                  </li>
              </ul>
            )
          } else {
            return null
          }
        } else {
          // not multiline text so must be a dict of key/value pairs
          return (
            <ul className='dashboard-quantities' key={text}>
              {Object.entries(texts[textName]).map(([quantity, measurement], lineNum) => (
                <li key={lineNum}>
                  {quantity}: {measurement}
                </li>
              ))}
            </ul>
          )
        }
      })}
    </div>
  )
}
NightReportText.propTypes = {
  nightReport: propTypes.object
}

function NightReport ({ initialNightReport, initialDate, camera, locationName, baseUrl }) {
  const [date, setDate] = useState(initialDate)
  const [nightReport, setNightReport] = useState(initialNightReport)

  useEffect(() => {
    function handleNightReportEvent (event) {
      console.debug('Nightreport event:', event)
      const { datestamp, data, dataType } = event.detail

      if (datestamp && datestamp !== date) {
        setDate(datestamp)
      }

      if (dataType === 'nightReport') {
        setNightReport(data)
      }
    }
    window.addEventListener('nightreport', handleNightReportEvent)

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('nightreport', handleNightReportEvent)
    }
  }, [date]) // Only reattach the event listener if the date changes

  const plots = nightReport.plots
  if (Object.entries(nightReport).length === 0) {
    return (
      <h3>There is no night report for today yet</h3>
    )
  }
  return (
    <div>
      <h3 id='the-date'>
        {camera.night_report_label} for: {initialDate}
      </h3>
      <div id='night-report'>
        <div className='plots-section tabs'>
          <div className='tab-titles'>
            <div id='tabtitle-text' className='tab-title disabled'>Efficiency</div>
            { groupBy(plots, plot => plot.group).map(([group, grouped]) => {
              let isDisabled = ''
              if (group === 'Elana' || group === 'elana') {
                isDisabled = 'disabled'
              }
              return (
                <div key={group} id={`tabtitle-${group.toLowerCase()}`} className={`tab-title ${isDisabled}`}>
                  {group}
                </div>
              )
            })}
          </div>

          <NightReportText nightReport={nightReport} />

          { groupBy(plots, plot => plot.group).map(([group, groupedPlots]) => (
            <div key={group} id={`tabgroup-${group.toLowerCase()}`} className='tab-content plots-grid'>
              {groupedPlots.map(plot => {
                const imgUrl = `${baseUrl}plot_image/${locationName}/${camera.name}/${group}/${plot.filename}.${plot.ext}`
                return (
                  <figure key={plot.filename} className='plot'>
                    <a href={imgUrl}>
                      <img src={imgUrl} alt={plot.filename} />
                    </a>
                    <figcaption>{plot.filename}</figcaption>
                  </figure>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
NightReport.propTypes = {
  initialDate: propTypes.string,
  initialNightReport: propTypes.object,
  camera: propTypes.object,
  locationName: propTypes.string,
  baseUrl: propTypes.string
}

export default NightReport

// A helper function to mimic Jinja2's groupby
function groupBy (array, keyFunction) {
  const obj = {}
  if (!array || array.length === 0) {
    return []
  }
  array.forEach(item => {
    const key = keyFunction(item)
    if (!obj[key]) {
      obj[key] = []
    }
    obj[key].push(item)
  })
  return Object.entries(obj)
}
