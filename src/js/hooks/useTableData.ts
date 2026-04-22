import { useState, useEffect, useCallback, useRef } from "react"
import {
  getHistoricalData,
  deserializeCompressedData,
  decodeChunk,
  assembleChunks,
  _getById,
} from "../modules/utils"
import { createTableFromStructuredData } from "../modules/convertTableData"
import {
  Camera,
  ChannelData,
  Metadata,
  MetadataRow,
} from "../components/componentTypes"

type EL = EventListener

function getLastMetadataRow(metadata: Metadata): MetadataRow | undefined {
  if (!metadata || Object.keys(metadata).length === 0) return undefined
  const lastSeq = Object.keys(metadata)
    .map(Number)
    .sort((a, b) => a - b)
    .pop()
  if (lastSeq === undefined) return undefined
  const row = metadata[lastSeq]
  return row && "Date begin" in row ? row : undefined
}

interface UseTableDataArgs {
  camera: Camera
  locationName: string
  initialDate: string
  isHistorical: boolean
  isStale: boolean
}

interface UseTableDataResult {
  date: string
  channelData: ChannelData
  metadata: Metadata
  hasReceivedData: boolean
  isLoadingMetadata: boolean
  metadataBytesReceived: number
  metadataTotalSize: number
  lastKnownMetadataRow: MetadataRow | undefined
  error: string | null
  setDateAndUpdateHeader: (newDate: string, stale?: boolean) => void
}

export default function useTableData({
  camera,
  locationName,
  initialDate,
  isHistorical,
  isStale,
}: UseTableDataArgs): UseTableDataResult {
  const [hasReceivedData, setHasReceivedData] = useState(false)
  const [date, setDate] = useState(initialDate)
  const [channelData, setChannelData] = useState({} as ChannelData)
  const [metadata, setMetadata] = useState({} as Metadata)
  const chunkBufferRef = useRef<Uint8Array[]>([])
  const hasMetadataRef = useRef(false)
  const isLoadingMetadataRef = useRef(false)
  const sawStreamStartRef = useRef(false)
  const [metadataBytesReceived, setMetadataBytesReceived] = useState(0)
  const [metadataTotalSize, _setMetadataTotalSize] = useState(0)
  const metadataTotalSizeRef = useRef(0)
  const setMetadataTotalSize = useCallback((v: number) => {
    metadataTotalSizeRef.current = v
    _setMetadataTotalSize(v)
  }, [])
  const [isLoadingMetadata, _setIsLoadingMetadata] = useState(false)
  const setIsLoadingMetadata = useCallback((v: boolean) => {
    isLoadingMetadataRef.current = v
    _setIsLoadingMetadata(v)
  }, [])
  const [lastKnownMetadataRow, setLastKnownMetadataRow] = useState<
    MetadataRow | undefined
  >(undefined)
  const [error, setError] = useState<string | null>(null)

  function setDateAndUpdateHeader(newDate: string, stale = false) {
    setDate(newDate)
    const headerDate = _getById("header-date") as HTMLSpanElement
    headerDate.textContent = newDate
    if (stale) {
      headerDate.classList.add("stale")
    } else {
      headerDate.classList.remove("stale")
    }
  }

  // Fetch historical data if required.
  // This effect runs only once when the component mounts.
  // It fetches data if the page is historical or stale.
  useEffect(() => {
    if (!isHistorical) {
      return
    }
    const t0 = performance.now()
    console.log(
      `[metadata] HTTP fetch started for ${locationName}/${camera.name}/${date}`
    )
    getHistoricalData(locationName, camera.name, date)
      .then((json) => {
        const elapsed = (performance.now() - t0).toFixed(0)
        const data = JSON.parse(json)
        const hasMetadata = !!data.metadata
        const hasStructured = !!(data.structuredData && data.extensionInfo)
        console.log(
          `[metadata] HTTP response received in ${elapsed}ms — ` +
            `structuredData=${hasStructured}, metadata=${hasMetadata}`
        )
        if (hasStructured) {
          const channelData = createTableFromStructuredData(
            camera.name,
            date,
            data.structuredData,
            data.extensionInfo,
            camera.channels
          )
          setChannelData(channelData)
        }
        if (data.metadata) {
          const parsed = deserializeCompressedData(data.metadata)
          if (parsed && Object.keys(parsed).length !== 0) {
            console.log(
              `[metadata] HTTP delivered metadata (${Object.keys(parsed).length} entries), ` +
                `setting hasMetadataRef=true`
            )
            setMetadata(parsed)
            hasMetadataRef.current = true
            // Clear any in-flight WS loading state — the HTTP response
            // already delivered the metadata so chunk processing will be
            // skipped and the progress bar must not linger.
            setIsLoadingMetadata(false)
            setMetadataBytesReceived(0)
            setMetadataTotalSize(0)
            chunkBufferRef.current = []
          }
        }
        // HTTP response had no metadata — it will arrive via WS chunks.
        // Show the progress bar immediately rather than waiting for the
        // first chunk to arrive.
        if (!hasMetadata && (hasStructured || data.perDay)) {
          console.log(
            "[metadata] HTTP response had no metadata — " +
              "showing progress bar for incoming WS stream"
          )
          setIsLoadingMetadata(true)
        }
        setDateAndUpdateHeader(data.date, isStale)
        if (data.structuredData || data.perDay || data.metadata) {
          setHasReceivedData(true)
        }
      })
      .catch((error) => {
        console.error("Error fetching historical data:", error.message)
        setError(error.message || "Failed to fetch historical data")
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle historical metadata streamed over WebSocket in chunks.
  const handleHistoricalDataUpdate = useCallback(
    (event: CustomEvent) => {
      const { dataType } = event.detail
      if (dataType === "metadataChunk") {
        if (hasMetadataRef.current) {
          // Metadata already loaded via HTTP — discard the WS stream
          // and ensure loading state is cleared.
          if (event.detail.final) {
            console.log(
              "[metadata] WS final chunk discarded — already loaded via HTTP"
            )
            chunkBufferRef.current = []
            setIsLoadingMetadata(false)
            setMetadataBytesReceived(0)
            setMetadataTotalSize(0)
          }
          return
        }
        const { payload, final: isFinal, totalSize, bytesSent } = event.detail
        if (!isFinal) {
          // First chunk doubles as stream start — initialise loading state.
          if (!isLoadingMetadataRef.current) {
            console.log(
              `[metadata] WS first chunk — ` +
                `starting loading (totalSize=${totalSize}, bytesSent=${bytesSent})`
            )
            chunkBufferRef.current = []
            setMetadataBytesReceived(0)
            setIsLoadingMetadata(true)
          }
          if (totalSize && !metadataTotalSizeRef.current)
            setMetadataTotalSize(totalSize)
          sawStreamStartRef.current = true
          const decompressed = decodeChunk(payload)
          chunkBufferRef.current.push(decompressed)
          console.log(
            `[metadata] WS chunk #${chunkBufferRef.current.length} — ` +
              `${decompressed.length} bytes, bytesSent=${bytesSent}/${totalSize}`
          )
          setMetadataBytesReceived(bytesSent)
        } else {
          const joinedMidStream = !sawStreamStartRef.current
          const chunks = chunkBufferRef.current
          // Reset for next stream.
          sawStreamStartRef.current = false
          chunkBufferRef.current = []
          setMetadataBytesReceived(0)
          setMetadataTotalSize(0)
          setIsLoadingMetadata(false)

          if (joinedMidStream) {
            // We missed the start of this stream so our buffer is
            // incomplete. The data is now cached server-side, so
            // fetch it via the API instead.
            console.log(
              "[metadata] WS final chunk — joined mid-stream, " +
                "fetching complete metadata from API"
            )
            getHistoricalData(locationName, camera.name, date)
              .then((json) => {
                const data = JSON.parse(json)
                if (data.metadata) {
                  const parsed = deserializeCompressedData(data.metadata)
                  if (parsed && Object.keys(parsed).length !== 0) {
                    console.log(
                      `[metadata] API re-fetch delivered metadata ` +
                        `(${Object.keys(parsed).length} entries)`
                    )
                    setMetadata(parsed)
                    hasMetadataRef.current = true
                    setHasReceivedData(true)
                  }
                }
              })
              .catch((e) =>
                console.error("Failed to re-fetch metadata from API:", e)
              )
            return
          }

          // Normal path — we saw the first chunk so buffer is complete.
          if (chunks.length === 0) {
            console.log(
              "[metadata] WS final chunk — empty buffer, nothing to parse"
            )
            return
          }
          const assembled = assembleChunks(chunks)
          console.log(
            `[metadata] WS final chunk — reassembling ${chunks.length} chunks, ` +
              `${assembled.length} total bytes`
          )
          try {
            const parsed = JSON.parse(new TextDecoder().decode(assembled))
            if (parsed && Object.keys(parsed).length !== 0) {
              console.log(
                `[metadata] WS metadata parsed OK (${Object.keys(parsed).length} entries)`
              )
              setMetadata(parsed)
              hasMetadataRef.current = true
              setHasReceivedData(true)
            }
          } catch (e) {
            console.error("Failed to parse reassembled metadata chunks:", e)
          }
        }
      } else if (dataType === "historicalStructuredData") {
        const { data } = event.detail
        if (data?.structuredData && data?.extensionInfo) {
          const channelData = createTableFromStructuredData(
            camera.name,
            data.date ?? date,
            data.structuredData,
            data.extensionInfo,
            camera.channels
          )
          if (Object.keys(channelData).length !== 0) {
            setChannelData(channelData)
            setHasReceivedData(true)
          }
        }
      }
    },
    [date, camera, locationName, setIsLoadingMetadata, setMetadataTotalSize]
  )

  useEffect(() => {
    window.addEventListener(
      "historicalDataUpdate",
      handleHistoricalDataUpdate as EL
    )
    return () => {
      window.removeEventListener(
        "historicalDataUpdate",
        handleHistoricalDataUpdate as EL
      )
    }
  }, [handleHistoricalDataUpdate])

  // Handle live camera events (current day).
  const handleCameraEvent = useCallback(
    (event: CustomEvent) => {
      const { datestamp, dataType } = event.detail

      if (dataType === "metadataChunk") {
        const { payload, final: isFinal, totalSize, bytesSent } = event.detail
        if (!isFinal) {
          if (!isLoadingMetadataRef.current) {
            chunkBufferRef.current = []
            if (totalSize !== undefined) setMetadataTotalSize(totalSize)
            setMetadataBytesReceived(0)
            // Set the ref directly (not the React state) so the guard
            // above only fires on the first chunk of a stream.  We
            // deliberately skip _setIsLoadingMetadata so the progress
            // bar does not render for current-day updates.
            isLoadingMetadataRef.current = true
          }
          const decompressed = decodeChunk(payload)
          chunkBufferRef.current.push(decompressed)
          setMetadataBytesReceived(bytesSent)
        } else {
          const chunks = chunkBufferRef.current
          chunkBufferRef.current = []
          setMetadataBytesReceived(0)
          setMetadataTotalSize(0)
          isLoadingMetadataRef.current = false
          if (chunks.length === 0) return
          try {
            const parsed = JSON.parse(
              new TextDecoder().decode(assembleChunks(chunks))
            )
            if (datestamp && datestamp !== date) {
              setLastKnownMetadataRow(getLastMetadataRow(parsed))
              setDateAndUpdateHeader(datestamp)
              setMetadata({})
              setChannelData({})
            }
            if (parsed && Object.keys(parsed).length !== 0) {
              setMetadata(parsed)
              setLastKnownMetadataRow(undefined)
              setHasReceivedData(true)
            }
          } catch (e) {
            console.error("Failed to parse reassembled metadata chunks:", e)
          }
        }
        return
      }

      const { data } = event.detail
      if (data.error) {
        setError(data.error)
      }

      // Before clearing metadata on day rollover, preserve the last metadata row
      if (datestamp && datestamp !== date) {
        if (dataType === "metadata" && Object.keys(data).length > 0) {
          setLastKnownMetadataRow(getLastMetadataRow(data))
        }
        setDateAndUpdateHeader(datestamp)
        setMetadata({})
        setChannelData({})
      }

      if (dataType === "metadata") {
        if (Object.keys(data).length !== 0) {
          setMetadata(data)
          setLastKnownMetadataRow(undefined)
          setHasReceivedData(true)
        }
      } else if (dataType === "channelData") {
        // Handle both old expanded format and new structured format
        // If data has structuredData and extensionInfo, convert it
        if (data.structuredData && data.extensionInfo) {
          const expandedChannelData = createTableFromStructuredData(
            camera.name,
            date,
            data.structuredData,
            data.extensionInfo,
            camera.channels
          )
          if (Object.keys(expandedChannelData).length !== 0) {
            setChannelData(expandedChannelData)
            setHasReceivedData(true)
          }
        } else {
          // Legacy: direct channel data (old expanded table format)
          if (Object.keys(data).length !== 0) {
            console.log(
              "Received legacy channel data update with datestamp:",
              datestamp
            )
            setChannelData(data)
            setHasReceivedData(true)
          }
        }
      }
    },
    [date, camera, setIsLoadingMetadata, setMetadataTotalSize]
  )

  useEffect(() => {
    window.addEventListener("camera", handleCameraEvent as EL)
    return () => {
      window.removeEventListener("camera", handleCameraEvent as EL)
    }
  }, [handleCameraEvent])

  return {
    date,
    channelData,
    metadata,
    hasReceivedData,
    isLoadingMetadata,
    metadataBytesReceived,
    metadataTotalSize,
    lastKnownMetadataRow,
    error,
    setDateAndUpdateHeader,
  }
}
