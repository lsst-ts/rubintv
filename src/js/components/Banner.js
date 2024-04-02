import React from 'react'

export default function Banner ({ siteLocation, locationName, camera }) {
  const camName = camera.name
  let banner = ''
  let cls = 'banner-text'
  if (camName === 'comcam_sim') {
    if (locationName === 'slac') {
      banner = 'USDF Nightly Validation Processing'
      cls += ' slac'
    } else {
      banner = 'Summit Quicklook Processing'
      cls += ' summit'
    }
  }
  return (
    banner &&
    <div className='banner-wrap'>
      <h2 className={ cls }>{ banner }</h2>
    </div>
  )
}
