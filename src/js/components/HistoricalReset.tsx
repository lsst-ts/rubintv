import React, { useState, useEffect, useRef, use } from "react"
import { WebsocketClient } from "js/modules/ws-service-client"
import { simplePost } from "js/modules/utils"

type HistoricalResetState = "idle" | "resetting" | "reset"

export default function HistoricalReset() {
  const [resetState, setResetState] = useState<HistoricalResetState>("idle")

  const websocketRef = useRef<WebsocketClient>(null)
  // Initialize the WebSocket client for historical status updates
  // This will create a new WebSocket connection when the component mounts
  useEffect(() => {
    websocketRef.current = new WebsocketClient()
    websocketRef.current.subscribe("historicalStatus")
    return () => {
      // Clean up the WebSocket connection when the component unmounts
      websocketRef.current?.close()
      websocketRef.current = null
    }
  }, [])

  const handleReset = (e: React.MouseEvent<HTMLButtonElement>) => {
    simplePost("api/historical_reset")
      .then(() => {
        setResetState("resetting")
      })
      .catch((err) => {
        console.error(`Couldn't reload historical data: ${err}`)
        setResetState("idle")
      })
  }

  const mockHandleReset = () => {
    // This function is for testing purposes only
    setResetState("resetting")
    setTimeout(() => {
      setResetState("reset")
    }, 2000) // Simulate a reset after 2 seconds
  }

  useEffect(() => {
    type EL = EventListener
    const handleStatusUpdate = (message: CustomEvent) => {
      const isBusy = message.detail.data
      if (!isBusy && resetState) {
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
        onClick={mockHandleReset}
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
