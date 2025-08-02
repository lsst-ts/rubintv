import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, act } from "@testing-library/react"
import PrevNext from "../PrevNext"
import { RubinTVTableContext } from "../componentTypes"

/* global jest, describe, it, expect, beforeEach, afterEach */

// Mock the utils module
jest.mock("../../modules/utils", () => ({
  setCameraBaseUrl: jest.fn((locationName, cameraName) => ({
    getEventUrl: jest.fn(
      (event) =>
        `http://test.com/event/${locationName}/${cameraName}/${event.seq_num}`
    ),
  })),
}))

describe("PrevNext Component", () => {
  const mockContextValue = {
    siteLocation: "summit",
    locationName: "test-location",
    camera: { name: "testcam", channels: [], title: "Test Cam" },
    dayObs: "2024-01-01",
  }

  const mockPrevNext = {
    prev: { seq_num: 12344, filename: "prev_image.jpg" },
    next: { seq_num: 12346, filename: "next_image.jpg" },
  }

  const mockPrevNextWithOnlyPrev = {
    prev: { seq_num: 12344, filename: "prev_image.jpg" },
    next: null,
  }

  const mockPrevNextWithOnlyNext = {
    prev: null,
    next: { seq_num: 12346, filename: "next_image.jpg" },
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  afterEach(() => {
    // Clean up any event listeners
    document.removeEventListener("keydown", jest.fn())
  })

  describe("Rendering", () => {
    it("renders null when initialPrevNext is null", () => {
      const { container } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={null} />
        </RubinTVTableContext.Provider>
      )

      expect(container.firstChild).toBeNull()
    })

    it("renders null when initialPrevNext is undefined", () => {
      const { container } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={undefined} />
        </RubinTVTableContext.Provider>
      )

      expect(container.firstChild).toBeNull()
    })

    it("renders both prev and next buttons when both are available", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevButton = screen.getByText("12344")
      const nextButton = screen.getByText("12346")

      expect(prevButton).toBeInTheDocument()
      expect(nextButton).toBeInTheDocument()
      expect(prevButton).toHaveClass("prev", "prev-next", "button")
      expect(nextButton).toHaveClass("next", "prev-next", "button")
    })

    it("renders only prev button when next is null", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNextWithOnlyPrev} />
        </RubinTVTableContext.Provider>
      )

      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.queryByText("12346")).not.toBeInTheDocument()
    })

    it("renders only next button when prev is null", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNextWithOnlyNext} />
        </RubinTVTableContext.Provider>
      )

      expect(screen.queryByText("12344")).not.toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()
    })

    it("renders with correct CSS classes", () => {
      const { container } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const wrapper = container.querySelector(".prev-next-buttons")
      expect(wrapper).toBeInTheDocument()

      const prevButton = screen.getByText("12344")
      const nextButton = screen.getByText("12346")

      expect(prevButton).toHaveClass("prev", "prev-next", "button")
      expect(nextButton).toHaveClass("next", "prev-next", "button")
    })
  })

  describe("URL Generation", () => {
    it("generates correct URLs for prev and next links", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")

      expect(prevLink).toHaveAttribute(
        "href",
        "http://test.com/event/test-location/testcam/12344"
      )
      expect(nextLink).toHaveAttribute(
        "href",
        "http://test.com/event/test-location/testcam/12346"
      )
    })

    it("uses context values for URL generation", () => {
      const { setCameraBaseUrl } = require("../../modules/utils")

      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(setCameraBaseUrl).toHaveBeenCalledWith("test-location", "testcam")
    })

    it("works with different context values", () => {
      const differentContext = {
        ...mockContextValue,
        locationName: "different-location",
        camera: { name: "differentcam", channels: [], title: "Different Cam" },
      }

      const { setCameraBaseUrl } = require("../../modules/utils")
      setCameraBaseUrl.mockReturnValue({
        getEventUrl: jest.fn(
          (event) =>
            `http://test.com/event/different-location/differentcam/${event.seq_num}`
        ),
      })

      render(
        <RubinTVTableContext.Provider value={differentContext}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(setCameraBaseUrl).toHaveBeenCalledWith(
        "different-location",
        "differentcam"
      )
    })
  })

  describe("Keyboard Navigation", () => {
    it("navigates to previous image when Left arrow key is pressed", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const clickSpy = jest.spyOn(prevLink, "click")

      fireEvent.keyDown(document, { key: "Left" })

      expect(clickSpy).toHaveBeenCalledTimes(1)
      clickSpy.mockRestore()
    })

    it("navigates to next image when Right arrow key is pressed", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const nextLink = screen.getByText("12346")
      const clickSpy = jest.spyOn(nextLink, "click")

      fireEvent.keyDown(document, { key: "Right" })

      expect(clickSpy).toHaveBeenCalledTimes(1)
      clickSpy.mockRestore()
    })

    it("does not navigate when Left key is pressed but no prev link exists", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNextWithOnlyNext} />
        </RubinTVTableContext.Provider>
      )

      // Should not throw error when no prev link exists
      expect(() => {
        fireEvent.keyDown(document, { key: "Left" })
      }).not.toThrow()
    })

    it("does not navigate when Right key is pressed but no next link exists", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNextWithOnlyPrev} />
        </RubinTVTableContext.Provider>
      )

      // Should not throw error when no next link exists
      expect(() => {
        fireEvent.keyDown(document, { key: "Right" })
      }).not.toThrow()
    })

    it("ignores other key presses", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")
      const prevClickSpy = jest.spyOn(prevLink, "click")
      const nextClickSpy = jest.spyOn(nextLink, "click")

      fireEvent.keyDown(document, { key: "Enter" })
      fireEvent.keyDown(document, { key: "Space" })
      fireEvent.keyDown(document, { key: "Escape" })
      fireEvent.keyDown(document, { key: "Tab" })

      expect(prevClickSpy).not.toHaveBeenCalled()
      expect(nextClickSpy).not.toHaveBeenCalled()

      prevClickSpy.mockRestore()
      nextClickSpy.mockRestore()
    })

    it("handles keyboard events with different key codes", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")
      const prevClickSpy = jest.spyOn(prevLink, "click")
      const nextClickSpy = jest.spyOn(nextLink, "click")

      // Test with different key representations
      fireEvent.keyDown(document, { key: "ArrowLeft" })
      fireEvent.keyDown(document, { key: "ArrowRight" })

      // These should not trigger navigation (only "Left" and "Right" strings)
      expect(prevClickSpy).not.toHaveBeenCalled()
      expect(nextClickSpy).not.toHaveBeenCalled()

      prevClickSpy.mockRestore()
      nextClickSpy.mockRestore()
    })
  })

  describe("Event Handling", () => {
    it("updates prevNext state when channel event with prevNext data is received", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      // Initially shows original data
      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()

      const newPrevNext = {
        prev: { seq_num: 99998, filename: "new_prev.jpg" },
        next: { seq_num: 100000, filename: "new_next.jpg" },
      }

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "prevNext",
            data: newPrevNext,
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Should show updated data
      expect(screen.getByText("99998")).toBeInTheDocument()
      expect(screen.getByText("100000")).toBeInTheDocument()
      expect(screen.queryByText("12344")).not.toBeInTheDocument()
      expect(screen.queryByText("12346")).not.toBeInTheDocument()
    })

    it("handles prevNext event with null values", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const newPrevNext = {
        prev: null,
        next: { seq_num: 12347, filename: "only_next.jpg" },
      }

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "prevNext",
            data: newPrevNext,
          },
        })
        window.dispatchEvent(channelEvent)
      })

      expect(screen.queryByText("12344")).not.toBeInTheDocument()
      expect(screen.getByText("12347")).toBeInTheDocument()
    })

    it("ignores channel events with different dataType", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "metadata",
            data: { some: "data" },
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Should still show original data
      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()
    })

    it("ignores channel events with no data", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "prevNext",
            data: null,
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Should still show original data
      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()
    })

    it("handles malformed channel events gracefully", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "prevNext",
            data: { invalid: "structure" },
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Component should handle this gracefully and not crash
      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()
    })
  })

  describe("Event Listener Cleanup", () => {
    it("removes keydown event listener on unmount", () => {
      const addEventListenerSpy = jest.spyOn(document, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(document, "removeEventListener")

      const { unmount } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })

    it("removes window channel event listener on unmount", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "channel",
        expect.any(Function)
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "channel",
        expect.any(Function)
      )

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })

    it("handles multiple mount/unmount cycles correctly", () => {
      const addDocumentEventListenerSpy = jest.spyOn(
        document,
        "addEventListener"
      )
      const addWindowEventListenerSpy = jest.spyOn(window, "addEventListener")

      const removeDocumentEventListenerSpy = jest.spyOn(
        document,
        "removeEventListener"
      )
      const removeWindowEventListenerSpy = jest.spyOn(
        window,
        "removeEventListener"
      )

      // First mount/unmount cycle
      const { unmount: unmount1 } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      unmount1()

      // Second mount/unmount cycle
      const { unmount: unmount2 } = render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      unmount2()

      // Should have called addEventListener and removeEventListener twice each
      expect(addWindowEventListenerSpy).toHaveBeenCalledTimes(2) // 2 times for each mount (channel)
      expect(addDocumentEventListenerSpy).toHaveBeenCalledTimes(2) // 2 times for each mount (keydown)
      expect(removeWindowEventListenerSpy).toHaveBeenCalledTimes(2) // 2 times for each unmount
      expect(removeDocumentEventListenerSpy).toHaveBeenCalledTimes(2) // 2 times for each unmount

      addWindowEventListenerSpy.mockRestore()
      addDocumentEventListenerSpy.mockRestore()
      removeWindowEventListenerSpy.mockRestore()
      removeDocumentEventListenerSpy.mockRestore()
    })
  })

  describe("Context Integration", () => {
    it("throws error when used outside RubinTVTableContext", () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()

      expect(() => {
        render(<PrevNext initialPrevNext={mockPrevNext} />)
      }).toThrow()

      consoleSpy.mockRestore()
    })

    it("works with different camera names in context", () => {
      const { setCameraBaseUrl } = require("../../modules/utils")
      const specialCameraContext = {
        ...mockContextValue,
        camera: { name: "special-camera", channels: [], title: "Special Cam" },
      }

      render(
        <RubinTVTableContext.Provider value={specialCameraContext}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(setCameraBaseUrl).toHaveBeenCalledWith(
        "test-location",
        "special-camera"
      )
    })
  })

  describe("Accessibility", () => {
    it("renders links with proper href attributes", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")

      expect(prevLink.tagName).toBe("A")
      expect(nextLink.tagName).toBe("A")
      expect(prevLink).toHaveAttribute("href")
      expect(nextLink).toHaveAttribute("href")
    })

    it("provides semantic meaning through CSS classes", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")

      expect(prevLink).toHaveClass("prev")
      expect(nextLink).toHaveClass("next")
    })
  })

  describe("Edge Cases", () => {
    it("handles prevNext with missing seq_num", () => {
      const malformedPrevNext = {
        prev: { filename: "prev_image.jpg" }, // Missing seq_num
        next: { seq_num: 12346, filename: "next_image.jpg" },
      }

      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={malformedPrevNext} />
        </RubinTVTableContext.Provider>
      )

      // Should render next button but handle missing seq_num gracefully
      expect(screen.getByText("12346")).toBeInTheDocument()
      // Prev button might not render properly, but component shouldn't crash
    })

    it("handles rapid state updates", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      // Rapid updates
      act(() => {
        for (let i = 0; i < 5; i++) {
          const newPrevNext = {
            prev: { seq_num: 10000 + i, filename: `prev_${i}.jpg` },
            next: { seq_num: 20000 + i, filename: `next_${i}.jpg` },
          }

          const channelEvent = new CustomEvent("channel", {
            detail: {
              dataType: "prevNext",
              data: newPrevNext,
            },
          })
          window.dispatchEvent(channelEvent)
        }
      })

      // Should show the last update
      expect(screen.getByText("10004")).toBeInTheDocument()
      expect(screen.getByText("20004")).toBeInTheDocument()
    })

    it("handles zero sequence numbers", () => {
      const zeroSeqPrevNext = {
        prev: { seq_num: 0, filename: "zero_prev.jpg" },
        next: { seq_num: 0, filename: "zero_next.jpg" },
      }

      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={zeroSeqPrevNext} />
        </RubinTVTableContext.Provider>
      )

      const buttons = screen.getAllByText("0")

      expect(buttons).toHaveLength(2) // Both prev and next have seq_num 0
      expect(buttons[0]).toHaveClass("prev")
    })

    it("handles very large sequence numbers", () => {
      const largeSeqPrevNext = {
        prev: { seq_num: 999999999, filename: "large_prev.jpg" },
        next: { seq_num: 1000000000, filename: "large_next.jpg" },
      }

      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={largeSeqPrevNext} />
        </RubinTVTableContext.Provider>
      )

      expect(screen.getByText("999999999")).toBeInTheDocument()
      expect(screen.getByText("1000000000")).toBeInTheDocument()
    })
  })

  describe("Integration Tests", () => {
    it("works end-to-end with keyboard navigation and event updates", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      // Test initial keyboard navigation
      const prevLink = screen.getByText("12344")
      const nextLink = screen.getByText("12346")
      const prevClickSpy = jest.spyOn(prevLink, "click")
      const nextClickSpy = jest.spyOn(nextLink, "click")

      fireEvent.keyDown(document, { key: "Left" })
      expect(prevClickSpy).toHaveBeenCalledTimes(1)

      fireEvent.keyDown(document, { key: "Right" })
      expect(nextClickSpy).toHaveBeenCalledTimes(1)

      prevClickSpy.mockRestore()
      nextClickSpy.mockRestore()

      // Update data via event
      const newPrevNext = {
        prev: { seq_num: 55555, filename: "updated_prev.jpg" },
        next: { seq_num: 66666, filename: "updated_next.jpg" },
      }

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            dataType: "prevNext",
            data: newPrevNext,
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Test keyboard navigation with updated data
      const newPrevLink = screen.getByText("55555")
      const newNextLink = screen.getByText("66666")

      const newPrevClickSpy = jest.spyOn(newPrevLink, "click")
      const newNextClickSpy = jest.spyOn(newNextLink, "click")

      fireEvent.keyDown(document, { key: "Left" })
      expect(newPrevClickSpy).toHaveBeenCalledTimes(1)

      fireEvent.keyDown(document, { key: "Right" })
      expect(newNextClickSpy).toHaveBeenCalledTimes(1)

      newPrevClickSpy.mockRestore()
      newNextClickSpy.mockRestore()
    })

    it("maintains proper state across multiple event types", () => {
      render(
        <RubinTVTableContext.Provider value={mockContextValue}>
          <PrevNext initialPrevNext={mockPrevNext} />
        </RubinTVTableContext.Provider>
      )

      // Send irrelevant events first
      act(() => {
        window.dispatchEvent(
          new CustomEvent("channel", {
            detail: { dataType: "metadata", data: {} },
          })
        )
        window.dispatchEvent(
          new CustomEvent("channel", {
            detail: { dataType: "image", data: {} },
          })
        )
      })

      // Original data should remain
      expect(screen.getByText("12344")).toBeInTheDocument()
      expect(screen.getByText("12346")).toBeInTheDocument()

      // Send relevant event
      act(() => {
        window.dispatchEvent(
          new CustomEvent("channel", {
            detail: {
              dataType: "prevNext",
              data: {
                prev: { seq_num: 77777, filename: "final_prev.jpg" },
                next: { seq_num: 88888, filename: "final_next.jpg" },
              },
            },
          })
        )
      })

      // Should show updated data
      expect(screen.getByText("77777")).toBeInTheDocument()
      expect(screen.getByText("88888")).toBeInTheDocument()
      expect(screen.queryByText("12344")).not.toBeInTheDocument()
      expect(screen.queryByText("12346")).not.toBeInTheDocument()
    })
  })
})
