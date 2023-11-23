import React, { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { groupBy } from '../modules/utils'

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
                          /* char code 160 is non-breaking space- used so that
                          formatted text lines up as expected. */
                          <p key={lineNum}>
                            {
                              line.replace('  ',
                                String.fromCharCode(160) +
                                String.fromCharCode(160))
                            }
                          </p>
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
              {Object.entries(texts[textName])
                .map(([quantity, measurement], lineNum) => (
                  <li key={lineNum}>
                    {quantity}: {measurement}
                  </li>
                ))
              }
            </ul>
          )
        }
      })}
    </div>
  )
}
NightReportText.propTypes = {
  /**
   * NightReportText objects have keys that are either `text_${num}` for which
   * the value is a multiline text string with newline (\n) delimeters or a
   * quality/measurement pair.
   */
  nightReport: PropTypes.object
}

function NightReport ({ initialNightReport, initialDate, camera, locationName, baseUrl }) {
  const [date, setDate] = useState(initialDate)
  const [nightReport, setNightReport] = useState(initialNightReport)

  useEffect(() => {
    function handleNightReportEvent (event) {
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

  if (Object.entries(nightReport).length === 0) {
    return (
      <h3>There is no night report for today yet</h3>
    )
  }
  const plots = nightReport.plots
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
              if (group.toLowerCase === 'elana') {
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
  /** The date in 'YYYY-MM-DD' format. */
  initialDate: PropTypes.string,
  /** NightReport object has optional 'plots' and/or 'text' properties.
   *  A plot object comprises the following string attributes:
   * {
   *  'key': (string) The key of the original object in the bucket.
   *  'hash': (string) The hash of the object.
   *  'camera': (string) The camera to which the plot belongs.
   *  'day_obs': (string) The date of the plot.
   *  'group': (string) The group to which the plot belongs.
   *  'filename': (string) The filename for the plot.
   *  'ext': (string) The file extension.
   * }
   * See NightReportText above for a brief description of the 'text' object.
   */
  initialNightReport: PropTypes.exact({
    plots: PropTypes.arrayOf(PropTypes.object),
    text: PropTypes.object
  }),
  /** The camera object. Please see rubin-tv/src/rubintv/models/models.py
   * for a full description.
  */
  camera: PropTypes.object,
  /** The name of the camera location. */
  locationName: PropTypes.string,
  /** Absolute base URL as defined by the app. Injected from the template to
   * avoid using js string wrangling to find it. Used to construct plot paths
   * for linking to.
   */
  baseUrl: PropTypes.string
}

export default NightReport
