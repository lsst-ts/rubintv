import React, { useState, useEffect, useRef } from "react"
import { WebsocketClient } from "../modules/ws-service-client"
import { simplePost } from "../modules/utils"

type HistoricalResetState = "idle" | "resetting" | "reset"
type EL = EventListener

export default function HistoricalReset() {
  const [resetState, setResetState] = useState<HistoricalResetState>("idle")

  const websocketRef = useRef<WebsocketClient>(null)
  // Initialize the WebSocket client for historical status updates
  // This will create a new WebSocket connection when the component mounts
  useEffect(() => {
    try {
      websocketRef.current = new WebsocketClient()
      websocketRef.current.subscribe("historicalStatus")
    } catch (error) {
      console.error(`Failed to initialize WebSocket: ${error}`)
    }
    return () => {
      // Clean up the WebSocket connection when the component unmounts
      websocketRef.current?.close()
      websocketRef.current = null
    }
  }, [])

  const handleReset = () => {
    setResetState("resetting")
    simplePost("api/historical_reset").catch((err) => {
      console.error(`Couldn't reload historical data: ${err}`)
      setResetState("idle")
    })
  }

  useEffect(() => {
    const handleStatusUpdate = (message: CustomEvent) => {
      const { data: isBusy } = message.detail || {}
      if (!isBusy) {
        setResetState("reset")
      }
    }
    window.addEventListener("historicalStatus", handleStatusUpdate as EL)
    return () => {
      window.removeEventListener("historicalStatus", handleStatusUpdate as EL)
    }
  }, [resetState])

  return (
    <div className="historical-reset">
      <button
        className="button"
        id="historicalReset"
        onClick={handleReset}
        disabled={resetState === "resetting"}
      >
        Reset Historical Data
        {resetState === "resetting" && (
          <span className="status">
            <img src="static/images/pending.gif" />
          </span>
        )}
      </button>
    </div>
  )
}
