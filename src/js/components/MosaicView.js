import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"
import { WebsocketClient } from "../modules/ws-service-client"
import {
  cameraType,
  channelDataType,
  eventType,
  metadataType,
  mosaicSingleView,
} from "./componentPropTypes"
import { simpleGet } from "../modules/utils"

const commonColumns = ["seqNum"]

export default function MosaicView({ camera, initialDate }) {
  const [date, setDate] = useState(initialDate)

  const initialViews = camera.mosaic_view_meta.map(view => (
    {
      ...view,
      latestEvent: {},
      latestMetadata: {}
    }))
  const [views, setViews] = useState(initialViews)

  useEffect(() => {
    function handleCurrentEvent (event) {
      const { datestamp, data, dataType } = event.detail
      console.log('Found:', datestamp, data, dataType)
    }
    window.addEventListener('channel', handleCurrentEvent)
  
    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('channel', handleCurrentEvent)
    }
  }) // Only reattach the event listener if the date changes

  return (
    <div className="viewsArea">
      <h3 className="viewsTitle">Mosaic View: <span className="date">{date}</span></h3>
      <ul className="views">
        {views.map((view) => {
          return (
            <li key={view.channel} className="view">
              <SingleView camera={camera} view={view} />
            </li>
          )
        })}
      </ul>
    </div>
  )
}
MosaicView.propTypes = {
  camera: cameraType,
  initialDate: PropTypes.string,
}

function SingleView({ camera, view }) {
  return (
    <>
      <CurrentImage camera={camera} event={view.latestEvent} />
      <SingleViewColumns viewMetaColumns={view.metaColumns} metadata={view.latestMetadata} />
    </>
  )
}
SingleView.propTypes = {
  camera: cameraType,
  view: mosaicSingleView,
}

function CurrentImage({ camera, event }) {
  return (
    <div className="viewImage">
      <img className="placeholder"/>
    </div>
  )
}
CurrentImage.propTypes = {
  camera: cameraType,
  event: eventType,
}

function SingleViewColumns({ viewMetaColumns, metadata }) {
  const columns = [...commonColumns, ...viewMetaColumns]
  return (
    <ul className="viewMeta">
      {columns.map((column) => {
        const value = metadata[column] ? metadata[column] : "No value set"
        return (
           <li key={column} className="viewMetaCol">
            <div className="colName">{column}</div>
            <div className="colValue">{value}</div>
           </li>
        )
      })}
    </ul>
  )
}
SingleViewColumns.propTypes = {
  viewMetaColumns: PropTypes.arrayOf(PropTypes.string),
  metadata: metadataType,
}

