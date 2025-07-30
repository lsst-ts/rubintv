import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"
import HistoricalReset from "../HistoricalReset"
import { WebsocketClient } from "../../modules/ws-service-client"
import { simplePost } from "../../modules/utils"

/* global jest, describe, it, expect, beforeEach, beforeAll, afterEach */

// Mock dependencies
jest.mock("../../modules/ws-service-client", () => ({
  WebsocketClient: jest.fn().mockImplementation(() => ({
    subscribe: jest.fn(),
    close: jest.fn(),
  })),
}))

jest.mock("../../modules/utils", () => ({
  simplePost: jest.fn(),
}))

describe("HistoricalReset Component", () => {
  let mockWebSocketClient

  beforeEach(() => {
    jest.clearAllMocks()
    mockWebSocketClient = {
      subscribe: jest.fn(),
      close: jest.fn(),
    }
    WebsocketClient.mockImplementation(() => mockWebSocketClient)
  })

  describe("Component Rendering", () => {
    it("renders the reset button in idle state", () => {
      render(<HistoricalReset />)

      const button = screen.getByRole("button", {
        name: "Reset Historical Data",
      })
      expect(button).toBeInTheDocument()
      expect(button).not.toBeDisabled()
      expect(button).toHaveAttribute("id", "historicalReset")
      expect(button).toHaveClass("button")
    })

    it("shows loading state when resetting", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button", {
        name: "Reset Historical Data",
      })

      await act(async () => {
        fireEvent.click(button)
      })

      await waitFor(() => {
        expect(button).toBeDisabled()
        expect(screen.getByRole("img")).toBeInTheDocument()
        expect(screen.getByRole("img")).toHaveAttribute(
          "src",
          "static/images/pending.gif"
        )
      })

      // Wait for the simplePost promise to resolve completely
      await waitFor(() => {
        expect(simplePost).toHaveBeenCalledWith("api/historical_reset")
      })
    })

    it("applies correct CSS classes", () => {
      const { container } = render(<HistoricalReset />)

      const wrapper = container.querySelector(".historical-reset")
      expect(wrapper).toBeInTheDocument()

      const button = screen.getByRole("button")
      expect(button).toHaveClass("button")
    })
  })

  describe("WebSocket Initialization", () => {
    it("initializes WebSocket client on mount", async () => {
      render(<HistoricalReset />)

      expect(WebsocketClient).toHaveBeenCalledTimes(1)
      expect(mockWebSocketClient.subscribe).toHaveBeenCalledWith(
        "historicalStatus"
      )
    })

    it("closes WebSocket connection on unmount", () => {
      const { unmount } = render(<HistoricalReset />)

      unmount()

      expect(mockWebSocketClient.close).toHaveBeenCalledTimes(1)
    })

    it("handles multiple mount/unmount cycles", () => {
      // First mount/unmount cycle
      const { unmount } = render(<HistoricalReset />)

      expect(WebsocketClient).toHaveBeenCalledTimes(1)
      expect(mockWebSocketClient.subscribe).toHaveBeenCalledTimes(1)

      unmount()
      expect(mockWebSocketClient.close).toHaveBeenCalledTimes(1)

      // Create new mock for second instance
      const secondMockClient = {
        subscribe: jest.fn(),
        close: jest.fn(),
      }
      WebsocketClient.mockImplementation(() => secondMockClient)

      // Second mount (separate render call)
      render(<HistoricalReset />)

      expect(WebsocketClient).toHaveBeenCalledTimes(2)
      expect(secondMockClient.subscribe).toHaveBeenCalledWith(
        "historicalStatus"
      )
    })
  })

  describe("Reset Functionality", () => {
    it("handles successful reset request", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(simplePost).toHaveBeenCalledWith("api/historical_reset")
        expect(button).toBeDisabled()
      })
    })

    it("handles failed reset request", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      const mockError = new Error("Reset failed")
      simplePost.mockRejectedValue(mockError)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "Couldn't reload historical data: Error: Reset failed"
        )
        expect(button).not.toBeDisabled()
      })

      consoleSpy.mockRestore()
    })

    it("prevents multiple simultaneous reset requests", async () => {
      simplePost.mockImplementation(() => new Promise(() => {})) // Never resolves

      render(<HistoricalReset />)

      const button = screen.getByRole("button")

      act(() => {
        fireEvent.click(button)
      })
      expect(button).toBeDisabled()

      // Try to click again while disabled
      fireEvent.click(button)

      expect(simplePost).toHaveBeenCalledTimes(1)
    })

    it("maintains disabled state during reset process", async () => {
      let resolvePromise
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      simplePost.mockReturnValue(pendingPromise)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // Button should remain disabled until process completes
      expect(button).toBeDisabled()

      act(() => {
        resolvePromise()
      })

      // Still disabled until WebSocket confirms completion
      expect(button).toBeDisabled()
    })
  })

  describe("WebSocket Event Handling", () => {
    it("handles historicalStatus events during reset", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // Simulate WebSocket event indicating reset is complete
      act(() => {
        const event = new CustomEvent("historicalStatus", {
          detail: { data: false }, // isBusy = false
        })
        window.dispatchEvent(event)
      })

      expect(button).not.toBeDisabled()
    })

    it("ignores historicalStatus events when not resetting", () => {
      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      expect(button).not.toBeDisabled()

      act(() => {
        const event = new CustomEvent("historicalStatus", {
          detail: { data: false },
        })
        window.dispatchEvent(event)
      })

      // Button should remain enabled
      expect(button).not.toBeDisabled()
    })

    it("handles historicalStatus events with busy status", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // Simulate WebSocket event indicating still busy
      act(() => {
        const event = new CustomEvent("historicalStatus", {
          detail: { data: true }, // isBusy = true
        })
        window.dispatchEvent(event)
      })

      // Should remain in resetting state
      expect(button).toBeDisabled()
      expect(screen.getByRole("img")).toBeInTheDocument()
    })

    it("removes event listener on unmount", () => {
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(<HistoricalReset />)

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "historicalStatus",
        expect.any(Function)
      )

      removeEventListenerSpy.mockRestore()
    })

    it("handles multiple historicalStatus events", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // Multiple busy events
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: true },
          })
        )
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: true },
          })
        )
      })

      expect(button).toBeDisabled()

      // Final completion event
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: false },
          })
        )
      })

      expect(button).not.toBeDisabled()
    })
  })

  describe("State Management", () => {
    it("transitions through states correctly", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")

      // Initial state: idle
      expect(button).not.toBeDisabled()
      expect(screen.queryByRole("img")).not.toBeInTheDocument()

      // Click to start reset
      fireEvent.click(button)

      // Transition to resetting state
      await waitFor(() => {
        expect(button).toBeDisabled()
        expect(screen.getByRole("img")).toBeInTheDocument()
      })

      // WebSocket event completes reset
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: false },
          })
        )
      })

      expect(button).not.toBeDisabled()
      expect(screen.queryByRole("img")).not.toBeInTheDocument()
    })

    it("handles state transitions with failed API call", async () => {
      simplePost.mockRejectedValue(new Error("API Error"))
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()

      render(<HistoricalReset />)

      const button = screen.getByRole("button")

      fireEvent.click(button)

      await waitFor(() => {
        expect(button).not.toBeDisabled() // Returns to idle state
        expect(screen.queryByRole("img")).not.toBeInTheDocument()
      })

      consoleSpy.mockRestore()
    })
  })

  describe("Error Handling", () => {
    it("logs detailed error information", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      const mockError = new Error("Network timeout")
      mockError.code = "TIMEOUT"
      simplePost.mockRejectedValue(mockError)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "Couldn't reload historical data: Error: Network timeout"
        )
      })

      consoleSpy.mockRestore()
    })

    it("handles WebSocket errors gracefully", () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()

      render(<HistoricalReset />)

      // Simulate malformed WebSocket event
      act(() => {
        try {
          window.dispatchEvent(
            new CustomEvent("historicalStatus", {
              detail: null, // Invalid detail
            })
          )
        } catch (error) {
          // Should not crash the component
        }
      })

      // Component should still be functional
      const button = screen.getByRole("button")
      expect(button).toBeInTheDocument()
      expect(button).not.toBeDisabled()

      consoleSpy.mockRestore()
    })

    it("handles WebSocket client creation failure", () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      WebsocketClient.mockImplementation(() => {
        throw new Error("WebSocket creation failed")
      })

      expect(() => render(<HistoricalReset />)).not.toThrow()

      consoleSpy.mockRestore()
    })
  })

  describe("Accessibility", () => {
    it("has proper button attributes", () => {
      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      expect(button).toHaveAttribute("id", "historicalReset")
      expect(button).toHaveAccessibleName("Reset Historical Data")
    })

    it("maintains accessibility during state changes", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toBeDisabled()
        expect(button).toHaveAccessibleName("Reset Historical Data")
      })
    })

    it("provides appropriate loading feedback", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      await waitFor(() => {
        const loadingImage = screen.getByRole("img")
        expect(loadingImage).toBeInTheDocument()
        expect(loadingImage).toHaveAttribute("src", "static/images/pending.gif")
      })
    })
  })

  describe("Memory Leaks Prevention", () => {
    it("cleans up all resources on unmount", () => {
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(<HistoricalReset />)

      unmount()

      expect(mockWebSocketClient.close).toHaveBeenCalledTimes(1)
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "historicalStatus",
        expect.any(Function)
      )

      removeEventListenerSpy.mockRestore()
    })

    it("handles unmount during pending operations", async () => {
      const pendingPromise = new Promise(() => {}) // Never resolves
      simplePost.mockReturnValue(pendingPromise)

      const { unmount } = render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      // Unmount while operation is pending
      unmount()

      expect(mockWebSocketClient.close).toHaveBeenCalledTimes(1)
    })

    it("does not update state after unmount", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      simplePost.mockResolvedValue(true)

      const { unmount } = render(<HistoricalReset />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      unmount()

      // Simulate WebSocket event after unmount
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: false },
          })
        )
      })

      // Should not cause any errors or warnings
      expect(consoleSpy).not.toHaveBeenCalled()

      consoleSpy.mockRestore()
    })
  })

  describe("Integration Tests", () => {
    it("completes full reset workflow", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")

      // 1. Initial state
      expect(button).not.toBeDisabled()
      expect(WebsocketClient).toHaveBeenCalledTimes(1)
      expect(mockWebSocketClient.subscribe).toHaveBeenCalledWith(
        "historicalStatus"
      )

      // 2. Start reset
      fireEvent.click(button)

      await waitFor(() => {
        expect(simplePost).toHaveBeenCalledWith("api/historical_reset")
        expect(button).toBeDisabled()
        expect(screen.getByRole("img")).toBeInTheDocument()
      })

      // 3. Complete reset via WebSocket
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: false },
          })
        )
      })

      // 4. Final state
      expect(button).not.toBeDisabled()
      expect(screen.queryByRole("img")).not.toBeInTheDocument()
    })

    it("handles rapid successive operations", async () => {
      simplePost.mockResolvedValue(true)

      render(<HistoricalReset />)

      const button = screen.getByRole("button")

      // First click
      fireEvent.click(button)
      await waitFor(() => expect(button).toBeDisabled())

      // Complete first operation
      act(() => {
        window.dispatchEvent(
          new CustomEvent("historicalStatus", {
            detail: { data: false },
          })
        )
      })

      expect(button).not.toBeDisabled()

      fireEvent.click(button)
      expect(simplePost).toHaveBeenCalledTimes(2)
    })
  })
})
