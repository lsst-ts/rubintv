import React, { createContext, useContext, memo, useMemo } from "react"
import { useState, useEffect, useRef } from "react"
import detectorMap from "../data/detectorMap.json"
import cwfsMap from "../data/cwfsMap.json"
import { simplePost } from "../modules/utils"
import { ModalProvider, useModal, ConfirmationModal } from "./Modal"

const RESET_PREFIX = "RUBINTV_CONTROL_RESET_"
const RedisEndpointContext = createContext(null)

const useRedisEndpoint = () => {
  const context = useContext(RedisEndpointContext)
  if (context === null) {
    throw new Error(
      "useRedisEndpoint must be used within a RedisEndpointProvider"
    )
  }
  return context
}

// Get status class name
const getStatusClass = (status) => {
  switch (status) {
    case "free":
      return "status-free"
    case "busy":
      return "status-busy"
    case "queued":
      return "status-queued"
    case "restarting":
      return "status-restarting"
    default:
      return "status-missing"
  }
}

const createPlaceholders = (count) => {
  const placeholders = {}
  for (let i = 0; i < count; i++) {
    placeholders[i] = { status: "missing" }
  }
  return placeholders
}

const DetectorSection = ({
  title,
  map,
  statuses,
  redisKey,
  size = "large",
}) => {
  return (
    <div className={`detector-section detector-section-${size}`}>
      <h2 className="detector-title">{title}</h2>
      <DetectorCanvas
        detectorMap={map}
        detectorStatuses={statuses}
        size={size}
      />
      <ResetButton redisKey={redisKey} />
    </div>
  )
}

const Cell = memo(({ prefix, index, status }) => (
  <div
    key={`${prefix}-${index}`}
    className={`detector-cell ${getStatusClass(status.status)}`}
  >
    {status.status === "queued" && (
      <div className="detector-cell-content queue-length">
        {status.queue_length}
      </div>
    )}
  </div>
))

const Cells = memo(({ statuses, prefix }) => {
  let activeWorkerCells = useMemo(() => {
    const cells = { ...statuses }
    const { numWorkers } = statuses
    if (numWorkers && numWorkers > 0) {
      delete cells.numWorkers
      const cellsToAdd = createPlaceholders(numWorkers)
      return {
        ...cellsToAdd,
        ...cells,
      }
    }
    return cells
  }, [statuses])

  return (
    <div className={`${prefix}-cells`}>
      {Object.entries(activeWorkerCells).map(([i, status]) => (
        <Cell
          key={`${prefix}-${i}`}
          prefix={prefix}
          index={i}
          status={status}
        />
      ))}
    </div>
  )
})

Cells.displayName = "Cells"
Cell.displayName = "Cell"

const ResetButton = ({ redisKey }) => {
  const [status, setStatus] = useState("")
  const { url: redisEndpointUrl, admin } = useRedisEndpoint()
  const { showModal, closeModal } = useModal()

  // Only show reset button if admin
  if (!admin) return null

  const handleReset = async () => {
    try {
      const resetKey = redisKey.replace("CLUSTER_STATUS_", RESET_PREFIX)
      const response = await simplePost(redisEndpointUrl, {
        key: resetKey,
        value: "reset",
      })
      if (response) {
        console.log("Reset successful")
        setStatus("success")
      } else {
        console.error("Reset failed:", response)
        setStatus("error")
      }
    } catch (error) {
      console.error("Error resetting detector:", error)
      setStatus("error")
    }
    closeModal()
  }

  const onClick = () => {
    showModal(
      <ConfirmationModal
        title="Confirm Reset"
        message="Are you sure you want to restart these workers?"
        onConfirm={handleReset}
        onCancel={closeModal}
      />
    )
  }

  const statusClass = `reset-button ${status}`
  return (
    <button className={statusClass} onClick={onClick}>
      Restart Workers
    </button>
  )
}

const DetectorStatusVisualization = ({
  detectorKeys,
  redisEndpointUrl,
  admin,
}) => {
  // redisKeys is a map of detector section names to their respective
  // keys in the Redis database
  // e.g. { sfmSet0: "CLUSTER_STATUS_SFM_SET_0", ... }
  const redisKeys = Object.fromEntries(detectorKeys.map((o) => [o.name, o.key]))

  const [mainDetectorStatuses, setMainDetectorStatuses] = useState({
    sfmSet0: {},
    sfmSet1: {},
    sfmStep1b: createPlaceholders(8),
    spareWorkers: createPlaceholders(4),
  })
  const [cwfsStatuses, setCwfsStatuses] = useState({
    aosSet0: {},
    aosSet1: {},
    aosSet2: {},
    aosSet3: {},
    aosStep1b: createPlaceholders(8),
  })
  const [otherQueues, setOtherQueues] = useState({})

  useEffect(() => {
    function handleDetectorEvent(event) {
      const { data, dataType } = event.detail

      if (dataType !== "detectorStatus") {
        return
      }
      // If we get here, treat it as a batch update
      const {
        sfmSet0,
        sfmSet1,
        sfmStep1b,
        spareWorkers,
        aosSet0,
        aosSet1,
        aosSet2,
        aosSet3,
        aosStep1b,
        otherQueues,
      } = data

      // Only update the detectors that have new data
      setMainDetectorStatuses((prev) => ({
        ...prev,
        ...(sfmSet0 && { sfmSet0 }),
        ...(sfmSet1 && { sfmSet1 }),
        ...(sfmStep1b && { sfmStep1b }),
        ...(spareWorkers && { spareWorkers }),
      }))

      setCwfsStatuses((prev) => ({
        ...prev,
        ...(aosSet0 && { aosSet0 }),
        ...(aosSet1 && { aosSet1 }),
        ...(aosSet2 && { aosSet2 }),
        ...(aosSet3 && { aosSet3 }),
        ...(aosStep1b && { aosStep1b }),
      }))

      if (otherQueues) {
        setOtherQueues((prev) => ({
          ...prev,
          ...otherQueues,
        }))
      }
    }

    // Add event listener for detector status updates
    window.addEventListener("detectors", handleDetectorEvent)

    // Cleanup listener on unmount
    return () => {
      window.removeEventListener("detectors", handleDetectorEvent)
    }
  }, [])

  return (
    <ModalProvider>
      <RedisEndpointContext.Provider value={{ url: redisEndpointUrl, admin }}>
        <div className="detector-container">
          <div className="legend">
            <div className="legend-items">
              <div className="legend-item">
                <div className="legend-color status-free"></div>
                <span>Free</span>
              </div>
              <div className="legend-item">
                <div className="legend-color status-busy"></div>
                <span>Busy</span>
              </div>
              <div className="legend-item">
                <div className="legend-color status-queued"></div>
                <span>Queued</span>
              </div>
              <div className="legend-item">
                <div className="legend-color status-missing"></div>
                <span>Missing</span>
              </div>
            </div>
          </div>
          <div className="main-detectors">
            <DetectorSection
              title="Imaging Worker Set 1"
              map={detectorMap}
              statuses={mainDetectorStatuses.sfmSet0}
              redisKey={redisKeys.sfmSet0}
              size="large"
            />
            <DetectorSection
              title="Imaging Worker Set 2"
              map={detectorMap}
              statuses={mainDetectorStatuses.sfmSet1}
              redisKey={redisKeys.sfmSet1}
              size="large"
            />
            <Step1bSection
              title="SFM Step 1b"
              statuses={mainDetectorStatuses.sfmStep1b}
              redisKey={redisKeys.sfmStep1b}
            />
          </div>
          <div className="aos-detectors">
            <DetectorSection
              title="CWFS Worker Set 1"
              map={cwfsMap}
              statuses={cwfsStatuses.aosSet0}
              redisKey={redisKeys.aosSet0}
              size="small"
            />
            <DetectorSection
              title="CWFS Worker Set 2"
              map={cwfsMap}
              statuses={cwfsStatuses.aosSet1}
              redisKey={redisKeys.aosSet1}
              size="small"
            />
            <DetectorSection
              title="CWFS Worker Set 3"
              map={cwfsMap}
              statuses={cwfsStatuses.aosSet2}
              redisKey={redisKeys.aosSet2}
              size="small"
            />
            <DetectorSection
              title="CWFS Worker Set 4"
              map={cwfsMap}
              statuses={cwfsStatuses.aosSet3}
              redisKey={redisKeys.aosSet3}
              size="small"
            />
            <Step1bSection
              title="AOS Step 1b"
              statuses={cwfsStatuses.aosStep1b}
              redisKey={redisKeys.aosStep1b}
            />
          </div>

          <div className="spareworkers-row">
            <h3>Backlog Workers</h3>
            <Cells
              statuses={mainDetectorStatuses.spareWorkers}
              prefix="spareworkers"
            />
          </div>
          <OtherQueuesSection otherQueues={otherQueues} />
        </div>
      </RedisEndpointContext.Provider>
    </ModalProvider>
  )
}

const OtherQueuesSection = ({ otherQueues }) => {
  return (
    <div className="other-queues-section">
      {Object.entries(otherQueues).length > 0 && (
        <div className="other-queues">
          <h3>Other Queues</h3>
          <table>
            <thead>
              <tr>
                <th>Queue Name</th>
                <th>Queue Length</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(otherQueues)
                .toSorted()
                .map(
                  ([key, value]) =>
                    value && (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{value}</td>
                      </tr>
                    )
                )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const Step1bSection = ({ title, statuses, redisKey }) => {
  return (
    <div className="step1b-section">
      <h2 className="detector-title">{title}</h2>
      <div className="step1b-canvas">
        <div className="step1b-cells">
          <Cells statuses={statuses} prefix="step1b" />
        </div>
      </div>
      <ResetButton redisKey={redisKey} />
    </div>
  )
}

const DetectorCell = memo(({ id, detector, status, calculatedValues }) => {
  const { toCanvasX, toCanvasY } = calculatedValues
  const { corners } = detector

  const cornerPoints = [
    corners.upperLeft,
    corners.upperRight,
    corners.lowerLeft,
    corners.lowerRight,
  ]

  const canvasCorners = {
    upperLeft: [toCanvasX(cornerPoints[0][0]), toCanvasY(cornerPoints[0][1])],
    upperRight: [toCanvasX(cornerPoints[1][0]), toCanvasY(cornerPoints[1][1])],
    lowerLeft: [toCanvasX(cornerPoints[2][0]), toCanvasY(cornerPoints[2][1])],
    lowerRight: [toCanvasX(cornerPoints[3][0]), toCanvasY(cornerPoints[3][1])],
  }

  const left = Math.min(canvasCorners.upperLeft[0], canvasCorners.lowerLeft[0])
  const top = Math.min(canvasCorners.upperLeft[1], canvasCorners.upperRight[1])
  const right = Math.max(
    canvasCorners.upperRight[0],
    canvasCorners.lowerRight[0]
  )
  const bottom = Math.max(
    canvasCorners.lowerLeft[1],
    canvasCorners.lowerRight[1]
  )

  const cellWidth = right - left
  const cellHeight = bottom - top
  const fontSize = Math.max(8, Math.min(cellWidth / 3, cellHeight / 3, 14))

  return (
    <div
      id={`${id}-cell`}
      className={`detector-cell ${getStatusClass(status.status)}`}
      style={{
        left: `${left}px`,
        top: `${top}px`,
        width: `${cellWidth}px`,
        height: `${cellHeight}px`,
      }}
    >
      <div className="detector-cell-content">
        {status.status === "queued" && (
          <div className="queue-length" style={{ fontSize: `${fontSize}px` }}>
            {status.queue_length}
          </div>
        )}
      </div>
    </div>
  )
})

DetectorCell.displayName = "DetectorCell"

const DetectorCanvas = memo(({ detectorMap, detectorStatuses }) => {
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: rect.width,
          height: rect.width,
        })
      }
    }

    const resizeObserver = new ResizeObserver(updateDimensions)
    resizeObserver.observe(containerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  const calculatedValues = useMemo(() => {
    const { width, height } = dimensions
    const padding = Math.min(width, height) * 0.1

    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity

    Object.values(detectorMap).forEach((detector) => {
      if (detector?.corners) {
        const corners = detector.corners
        const cornerPoints = [
          corners.upperLeft,
          corners.upperRight,
          corners.lowerLeft,
          corners.lowerRight,
        ]
        if (
          cornerPoints.every(
            (corner) => Array.isArray(corner) && corner.length >= 2
          )
        ) {
          cornerPoints.forEach((corner) => {
            minX = Math.min(minX, corner[0])
            maxX = Math.max(maxX, corner[0])
            minY = Math.min(minY, corner[1])
            maxY = Math.max(maxY, corner[1])
          })
        }
      }
    })

    if (
      minX === Infinity ||
      maxX === -Infinity ||
      minY === Infinity ||
      maxY === -Infinity
    ) {
      return null
    }

    const dataWidth = maxX - minX
    const dataHeight = maxY - minY
    const scale = Math.min(
      (width - 2 * padding) / dataWidth,
      (height - 2 * padding) / dataHeight
    )

    return {
      padding,
      scale,
      toCanvasX: (x) => (x - minX) * scale + padding,
      toCanvasY: (y) => (maxY - y) * scale + padding,
      width,
      height,
    }
  }, [dimensions, detectorMap])

  if (!calculatedValues || calculatedValues.width === 0) {
    return <div ref={containerRef} className="detector-canvas" />
  }

  return (
    <div ref={containerRef} className="detector-canvas">
      {Object.entries(detectorMap).map(([id, detector]) => {
        if (!detector?.corners) return null

        const status = detectorStatuses[id] || {
          status: "unknown",
          queue_length: 0,
        }

        return (
          <DetectorCell
            key={id}
            id={id}
            detector={detector}
            status={status}
            calculatedValues={calculatedValues}
          />
        )
      })}
    </div>
  )
})

DetectorCanvas.displayName = "DetectorCanvas"

export default DetectorStatusVisualization
