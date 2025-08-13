import React, { useContext, memo, useMemo } from "react"
import { useState, useEffect, useRef } from "react"
import detectorMap from "../data/detectorMap.json"
import cwfsMap from "../data/cwfsMap.json"
import { simplePost } from "../modules/utils"
import { ModalProvider, useModal, ConfirmationModal } from "./Modal"
import {
  DetectorMap,
  DetectorKey,
  WorkerGroup,
  WorkerStatus,
  StatusSet,
  RedisEndpointContext,
} from "./componentTypes"
import {
  RESET_PREFIX,
  getStatusClass,
  getStatusColor,
  createPlaceholders,
} from "../modules/detectorUtils"

export { DetectorCanvas, Cell, ResetButton, OtherQueuesSection, Cells }

export const useRedisEndpoint = () => {
  const context = useContext(RedisEndpointContext)
  if (context === null) {
    throw new Error(
      "useRedisEndpoint must be used within a RedisEndpointProvider"
    )
  }
  return context
}

const DetectorSection = ({
  title,
  map,
  statuses,
  redisKey,
  size = "large",
}: {
  title: string
  map: DetectorMap
  statuses: StatusSet
  redisKey: string
  size?: "small" | "large"
}) => {
  return (
    <div className={`detector-section detector-section-${size}`}>
      <h2 className="detector-title">{title}</h2>
      <DetectorCanvas detectorMap={map} detectorStatuses={statuses} />
      <ResetButton redisKey={redisKey} />
    </div>
  )
}

const Cells = memo(
  ({ statuses, prefix }: { statuses: WorkerGroup; prefix: string }) => {
    const activeWorkerCells = useMemo(() => {
      const cells = { ...statuses.workers }
      const { numWorkers } = statuses
      if (numWorkers && numWorkers > 0) {
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
          <Cell key={`${prefix}-${i}`} status={status as WorkerStatus} />
        ))}
      </div>
    )
  }
)
Cells.displayName = "Cells"

function Cell({ status }: { status: WorkerStatus }) {
  return (
    <div className={`detector-cell ${getStatusClass(status.status)}`}>
      {status.status === "queued" && (
        <div className="detector-cell-content queue-length">
          {status.queue_length}
        </div>
      )}
    </div>
  )
}

const ResetButton = ({ redisKey }: { redisKey: string }) => {
  const [status, setStatus] = useState("")
  const { url: redisEndpointUrl, admin } = useRedisEndpoint()
  const { showModal, closeModal } = useModal()

  // Only show reset button if admin
  if (!admin) return null

  const showStatusDelay = (status: string) => {
    setStatus(status)
    setTimeout(() => {
      setStatus("")
    }, 2000)
  }

  const handleReset = async () => {
    try {
      const resetKey = redisKey.replace("CLUSTER_STATUS_", RESET_PREFIX)
      const response = await simplePost(redisEndpointUrl, {
        key: resetKey,
        value: "reset",
      })
      if (response) {
        console.log("Reset successful")
        showStatusDelay("success")
      } else {
        console.error("Reset failed:", response)
        showStatusDelay("error")
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
        onConfirm={() => {
          void handleReset()
        }}
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
}: {
  detectorKeys: DetectorKey[]
  redisEndpointUrl: string
  admin: boolean
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
    type EL = EventListener
    function handleDetectorEvent(event: CustomEvent) {
      const { data, dataType } = event.detail
      if (dataType !== "detectorStatus") {
        return
      }
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

    window.addEventListener("detectors", handleDetectorEvent as EL)

    return () => {
      window.removeEventListener("detectors", handleDetectorEvent as EL)
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
                <div className="legend-color status-restarting"></div>
                <span>Restarting</span>
              </div>
              <div className="legend-item">
                <div className="legend-color status-guest"></div>
                <span>Guest payload</span>
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
            <div className="spareworkers-section">
              <h3>Backlog Workers</h3>
              <Cells
                statuses={mainDetectorStatuses.spareWorkers}
                prefix="spareworkers"
              />
              <ResetButton redisKey={redisKeys.spareWorkers} />
            </div>
          </div>
          <OtherQueuesSection otherQueues={otherQueues} />
        </div>
      </RedisEndpointContext.Provider>
    </ModalProvider>
  )
}

const OtherQueuesSection = ({ otherQueues }: { otherQueues: WorkerGroup }) => {
  const { text } = otherQueues
  return (
    <div className="other-queues-section">
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
            {Object.entries(text || {})
              .slice()
              .sort()
              .map(
                ([key, value]) =>
                  value.toString() != "" && (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{value}</td>
                    </tr>
                  )
              )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const Step1bSection = ({
  title,
  statuses,
  redisKey,
}: {
  title: string
  statuses: StatusSet["sfmStep1b"]
  redisKey: string
}) => {
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

const DetectorCanvas = memo(
  ({
    detectorMap,
    detectorStatuses,
  }: {
    detectorMap: DetectorMap
    detectorStatuses: WorkerGroup
  }) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

    useEffect(() => {
      const updateDimensions = () => {
        if (containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect()
          const width = rect.width
          const height = rect.width // Keep square aspect ratio
          setDimensions({ width, height })
        }
      }

      const resizeObserver = new ResizeObserver(updateDimensions)
      if (containerRef.current) {
        resizeObserver.observe(containerRef.current)
      }

      return () => resizeObserver.disconnect()
    }, [])

    useEffect(() => {
      if (!canvasRef.current || !dimensions.width) return

      const canvas = canvasRef.current
      const ctx = canvas.getContext("2d") as CanvasRenderingContext2D
      const dpr = window.devicePixelRatio || 1

      canvas.width = dimensions.width * dpr
      canvas.height = dimensions.height * dpr
      ctx.scale(dpr, dpr)

      // Calculate scaling factors
      let minX = Infinity,
        maxX = -Infinity,
        minY = Infinity,
        maxY = -Infinity
      Object.values(detectorMap).forEach((detector) => {
        if (!detector?.corners) return
        Object.values(detector.corners).forEach((corner) => {
          minX = Math.min(minX, corner[0])
          maxX = Math.max(maxX, corner[0])
          minY = Math.min(minY, corner[1])
          maxY = Math.max(maxY, corner[1])
        })
      })

      const padding = dimensions.width * 0.1
      const dataWidth = maxX - minX
      const dataHeight = maxY - minY
      const scale = Math.min(
        (dimensions.width - 2 * padding) / dataWidth,
        (dimensions.height - 2 * padding) / dataHeight
      )

      const toCanvasX = (x: number) => (x - minX) * scale + padding
      const toCanvasY = (y: number) => (maxY - y) * scale + padding

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Update stroke style to match Sass border color
      ctx.strokeStyle = "#374151"
      ctx.lineWidth = 1 * dpr

      Object.entries(detectorMap).forEach(([id, detector]) => {
        const status = detectorStatuses.workers?.[id] || {
          status: "unknown",
          queue_length: 0,
        }

        ctx.globalAlpha = 0.9

        const { upperLeft, upperRight, lowerLeft, lowerRight } =
          detector.corners

        // Draw detector cell
        ctx.beginPath()
        ctx.moveTo(...[toCanvasX(upperLeft[0]), toCanvasY(upperLeft[1])])
        ctx.lineTo(...[toCanvasX(upperRight[0]), toCanvasY(upperRight[1])])
        ctx.lineTo(...[toCanvasX(lowerRight[0]), toCanvasY(lowerRight[1])])
        ctx.lineTo(...[toCanvasX(lowerLeft[0]), toCanvasY(lowerLeft[1])])
        ctx.closePath()

        // Fill based on status
        ctx.fillStyle = getStatusColor(status.status)
        ctx.fill()
        ctx.stroke()

        // Reset alpha for text
        ctx.globalAlpha = 1
        if (status.status === "queued") {
          const centerX = toCanvasX((upperLeft[0] + lowerRight[0]) / 2)
          const centerY = toCanvasY((upperLeft[1] + lowerRight[1]) / 2)
          const cellWidth = toCanvasX(upperRight[0]) - toCanvasX(upperLeft[0])
          const fontSize = Math.max(14, Math.min(cellWidth / 3, 14))

          ctx.fillStyle = "white" // Match Sass queue length color
          ctx.font = `bold ${fontSize}px Arial` // Match Sass font weight
          ctx.textAlign = "center"
          ctx.textBaseline = "middle"
          if (status.queue_length !== undefined) {
            ctx.fillText(status.queue_length.toString(), centerX, centerY)
          }
        }
      })
    }, [detectorMap, detectorStatuses, dimensions])

    return (
      <div ref={containerRef} className="detector-canvas">
        <canvas ref={canvasRef} />
      </div>
    )
  }
)
DetectorCanvas.displayName = "DetectorCanvas"

export default DetectorStatusVisualization
