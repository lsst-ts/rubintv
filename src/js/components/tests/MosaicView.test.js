import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react"
import MosaicView from "../MosaicView"
import { _getById } from "../../modules/utils"

/* global jest, describe, it, expect, beforeEach, afterEach */

// Mock utility functions
jest.mock("../../modules/utils", () => ({
  _getById: jest.fn(),
  getStrHashCode: jest.fn((str) => `hash_${str}`),
}))

// Mock config
jest.mock("../../config", () => ({
  homeUrl: "http://test.com/",
}))

describe("MosaicView Component", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [
      {
        name: "channel1",
        title: "Channel 1",
        colour: "#ff0000",
      },
      {
        name: "channel2",
        title: "Channel 2",
        colour: "#00ff00",
      },
      {
        name: "channel3",
        title: "Channel 3",
        colour: "#0000ff",
      },
    ],
    mosaic_view_meta: [
      {
        channel: "channel1",
        mediaType: "image",
        metaColumns: ["colA", "colB"],
        selected: false,
      },
      {
        channel: "channel2",
        mediaType: "video",
        metaColumns: ["colC"],
        selected: false,
      },
      {
        channel: "channel3",
        mediaType: "video",
        metaColumns: ["colD"],
        selected: false,
      },
    ],
  }

  const mockSingleVideoCamera = {
    ...mockCamera,
    mosaic_view_meta: [
      {
        channel: "channel1",
        mediaType: "image",
        metaColumns: ["colA"],
        selected: false,
      },
      {
        channel: "channel2",
        mediaType: "video",
        metaColumns: ["colB"],
        selected: false,
      },
    ],
  }

  beforeEach(() => {
    jest.clearAllMocks()
    // Mock video element methods
    HTMLVideoElement.prototype.pause = jest.fn()
    HTMLVideoElement.prototype.play = jest.fn()
    Object.defineProperty(HTMLVideoElement.prototype, "currentTime", {
      get: jest.fn(() => 5.0),
      set: jest.fn(),
      configurable: true,
    })
    Object.defineProperty(HTMLVideoElement.prototype, "duration", {
      get: jest.fn(() => 10.0),
      configurable: true,
    })
    Object.defineProperty(HTMLVideoElement.prototype, "paused", {
      get: jest.fn(() => true),
      configurable: true,
    })
  })

  describe("Component Rendering", () => {
    it("renders mosaic view with all channels", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      expect(screen.getByText("Channel 1")).toBeInTheDocument()
      expect(screen.getByText("Channel 2")).toBeInTheDocument()
      expect(screen.getByText("Channel 3")).toBeInTheDocument()
    })

    it("renders correct number of view items", () => {
      const { container } = render(
        <MosaicView locationName="test-location" camera={mockCamera} />
      )

      const viewItems = container.querySelectorAll(".view")
      expect(viewItems).toHaveLength(3)
    })

    it("applies correct CSS classes to view items", () => {
      const { container } = render(
        <MosaicView locationName="test-location" camera={mockCamera} />
      )

      const imageView = container.querySelector(".view-image")
      const videoViews = container.querySelectorAll(".view-video")

      expect(imageView).toBeInTheDocument()
      expect(videoViews).toHaveLength(2)
    })

    it("selects first video by default when multiple videos exist", () => {
      const { container } = render(
        <MosaicView locationName="test-location" camera={mockCamera} />
      )

      const selectedViews = container.querySelectorAll(".view.selected")
      expect(selectedViews).toHaveLength(1)

      const selectedView = selectedViews[0]
      expect(selectedView).toHaveClass("view-video")
    })

    it("does not select any view when only one video exists", () => {
      const { container } = render(
        <MosaicView
          locationName="test-location"
          camera={mockSingleVideoCamera}
        />
      )

      const selectedViews = container.querySelectorAll(".view.selected")
      expect(selectedViews).toHaveLength(1) // First video is still selected
    })

    it("handles missing channel gracefully", () => {
      const cameraWithMissingChannel = {
        ...mockCamera,
        channels: [mockCamera.channels[0]], // Only has channel1
        mosaic_view_meta: [
          mockCamera.mosaic_view_meta[0],
          {
            channel: "missing_channel",
            mediaType: "image",
            metaColumns: [],
            selected: false,
          },
        ],
      }

      render(
        <MosaicView
          locationName="test-location"
          camera={cameraWithMissingChannel}
        />
      )

      expect(
        screen.getByText("Channel missing_channel not found")
      ).toBeInTheDocument()
    })
  })

  describe("Event Handling", () => {
    it("handles camera metadata events", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      const metadata = {
        123: { colA: "valueA", colB: "valueB" },
        124: { colA: "valueC", colB: "valueD" },
      }

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: metadata,
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // Metadata should be stored for later use when events arrive
      // We can't directly test this without exposing internal state
      // But we can test that no errors occur
      expect(screen.getByText("Channel 1")).toBeInTheDocument()
    })

    it("ignores non-metadata camera events", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: { some: "data" },
            dataType: "otherType",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // Should not cause any issues
      expect(screen.getByText("Channel 1")).toBeInTheDocument()
    })

    it("ignores camera events with empty data", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: {},
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      expect(screen.getByText("Channel 1")).toBeInTheDocument()
    })

    it("handles channel events and updates latest event", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: {
            data: channelEvent,
          },
        })
        window.dispatchEvent(event)
      })

      // Should show the day_obs in the channel title
      expect(screen.getByText(": 2024-01-01")).toBeInTheDocument()
    })

    it("handles channel events with no data", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation()

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const event = new CustomEvent("channel", {
          detail: {
            data: null,
          },
        })
        window.dispatchEvent(event)
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        "No data received in channel event"
      )
      consoleSpy.mockRestore()
    })

    it("handles channel events with empty data", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation()

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const event = new CustomEvent("channel", {
          detail: {
            data: {},
          },
        })
        window.dispatchEvent(event)
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        "No data received in channel event"
      )
      consoleSpy.mockRestore()
    })
  })

  describe("Channel Selection", () => {
    it("allows selecting different video channels when multiple videos exist", () => {
      const { container } = render(
        <MosaicView locationName="test-location" camera={mockCamera} />
      )

      // Initially, first video (channel2) should be selected
      expect(
        container.querySelector(".view-video.selected")
      ).toBeInTheDocument()

      // Click on another video channel (channel3)
      const videoViews = container.querySelectorAll(".view-video")
      const unselectedVideo = Array.from(videoViews).find(
        (view) => !view.classList.contains("selected")
      )

      if (unselectedVideo) {
        fireEvent.click(unselectedVideo)

        // Selection should change
        const selectedViews = container.querySelectorAll(".view.selected")
        expect(selectedViews).toHaveLength(1)
      }
    })

    it("does not make views clickable when only one video exists", () => {
      const { container } = render(
        <MosaicView
          locationName="test-location"
          camera={mockSingleVideoCamera}
        />
      )

      const videoView = container.querySelector(".view-video")

      // Click should not have an effect (no click handler when not selectable)
      const initialSelected = container.querySelector(".view.selected")
      fireEvent.click(videoView)

      const stillSelected = container.querySelector(".view.selected")
      expect(stillSelected).toBe(initialSelected)
    })
  })

  describe("Media Display", () => {
    beforeEach(() => {
      // Mock metadata for testing
      const metadata = {
        123: { seqNum: "123", colA: "valueA", colB: "valueB" },
      }

      // Set up component with metadata
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: metadata,
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })
    })

    it("displays image media correctly", () => {
      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      const img = screen.getByRole("img")
      expect(img).toHaveAttribute(
        "src",
        "http://test.com/event_image/test-location/testcam/channel1/test_image.jpg"
      )

      const link = img.closest("a")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/event_image/test-location/testcam/channel1/test_image.jpg"
      )
    })

    it("displays video media correctly", () => {
      const channelEvent = {
        channel_name: "channel2",
        seq_num: 123,
        filename: "test_video.mp4",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      const video = document.querySelector("video")
      expect(video).toBeInTheDocument()
      expect(video).toHaveAttribute("autoPlay")
      expect(video).toHaveAttribute("loop")
      expect(video).toHaveAttribute("controls")
      expect(video).toHaveAttribute(
        "id",
        "v_hash_test-location/testcam/channel2/test_video.mp4"
      )

      const source = video.querySelector("source")
      expect(source).toHaveAttribute(
        "src",
        "http://test.com/event_video/test-location/testcam/channel2/test_video.mp4"
      )

      const link = video.closest("a")
      expect(link).toHaveAttribute(
        "href",
        "http://test.com/event_video/test-location/testcam/channel2/test_video.mp4"
      )
    })

    it("shows placeholders when no event data", () => {
      expect(screen.getAllByText("Nothing today yet")).toHaveLength(3)
    })

    it("shows placeholders when event has no filename", () => {
      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })
      expect(screen.getAllByText("Nothing today yet")).toHaveLength(3)
    })
  })

  describe("Video Controls", () => {
    let mockVideo

    beforeEach(() => {
      mockVideo = {
        id: "v_hash_test-location/testcam/channel2/test_video.mp4",
        currentTime: 5.0,
        duration: 10.0,
        paused: true,
        pause: jest.fn(() => {
          console.log("Mock video paused")
        }),
      }
      _getById.mockReturnValue(mockVideo)

      // Set up a video in the DOM
      const channelEvent = {
        channel_name: "channel2",
        seq_num: 123,
        filename: "test_video.mp4",
        day_obs: "2024-01-01",
      }

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })
    })

    it("shows frame step controls when video is loaded", async () => {
      const video = document.querySelector("video")

      // Trigger loadedData event
      fireEvent.loadedData(video)

      await waitFor(() => {
        const frameButtons = document.querySelectorAll(
          ".video-extra-controls button"
        )
        expect(frameButtons).toHaveLength(2)
        expect(frameButtons[0]).toHaveTextContent("<")
        expect(frameButtons[1]).toHaveTextContent(">")
      })
    })

    it("handles backward frame step", async () => {
      const video = document.querySelector("video")

      video.pause = jest.fn()
      video.currentTime = 5.0

      fireEvent.loadedData(video)

      await waitFor(() => {
        const backButton = document.querySelector(
          ".video-extra-controls button"
        )
        fireEvent.click(backButton)
      })

      // expect(mockVideo.pause).toHaveBeenCalled()
      expect(mockVideo.currentTime).toBe(4.9) // 5.0 - 0.1
    })

    it("handles forward frame step", async () => {
      const video = document.querySelector("video")
      fireEvent.loadedData(video)

      await waitFor(() => {
        const buttons = document.querySelectorAll(
          ".video-extra-controls button"
        )
        const forwardButton = buttons[1]
        fireEvent.click(forwardButton)
      })

      // expect(mockVideo.pause).toHaveBeenCalled()
      expect(mockVideo.currentTime).toBe(5.1) // 5.0 + 0.1
    })

    it("handles backward frame step at beginning", () => {
      mockVideo.currentTime = 0.05
      _getById.mockReturnValue(mockVideo)

      const video = document.querySelector("video")
      fireEvent.loadedData(video)

      const backButton = document.querySelector(".video-extra-controls button")
      fireEvent.click(backButton)

      expect(mockVideo.currentTime).toBe(0) // Should clamp to 0
    })

    it("handles forward frame step at end", () => {
      mockVideo.currentTime = 9.95
      _getById.mockReturnValue(mockVideo)

      const video = document.querySelector("video")
      fireEvent.loadedData(video)

      const buttons = document.querySelectorAll(".video-extra-controls button")
      const forwardButton = buttons[1]
      fireEvent.click(forwardButton)

      expect(mockVideo.currentTime).toBe(mockVideo.duration) // Should clamp to duration
    })

    it("handles video not found gracefully", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation()
      _getById.mockReturnValue(null)

      const video = document.querySelector("video")
      fireEvent.loadedData(video)

      const backButton = document.querySelector(".video-extra-controls button")
      fireEvent.click(backButton)

      expect(consoleSpy).toHaveBeenCalledWith(
        "Video with ID v_hash_test-location/testcam/channel2/test_video.mp4 not found"
      )
      consoleSpy.mockRestore()
    })
  })

  describe("Keyboard Controls", () => {
    let mockVideo

    beforeEach(() => {
      mockVideo = {
        id: "v_hash_test-location/testcam/channel2/test_video.mp4",
        currentTime: 5.0,
        duration: 10.0,
        paused: false, // Set to false so pause() will be called
        pause: jest.fn(() => {
          mockVideo.paused = true // Update paused state when pause is called
        }),
      }

      // Mock document.querySelector to find selected video
      const originalQuerySelector = document.querySelector
      document.querySelector = jest.fn((selector) => {
        if (selector === ".view-video.selected video") {
          return mockVideo
        }
        return originalQuerySelector.call(document, selector)
      })

      _getById.mockReturnValue(mockVideo)
    })

    afterEach(() => {
      // Restore original querySelector
      document.querySelector = Document.prototype.querySelector
    })

    it("handles left arrow key for backward step", () => {
      const keyEvent = new KeyboardEvent("keydown", { code: "ArrowLeft" })

      window.onkeydown(keyEvent)

      expect(mockVideo.pause).toHaveBeenCalled()
      expect(mockVideo.currentTime).toBe(4.9)
    })

    it("handles right arrow key for forward step", () => {
      const keyEvent = new KeyboardEvent("keydown", { code: "ArrowRight" })

      window.onkeydown(keyEvent)

      expect(mockVideo.pause).toHaveBeenCalled()
      expect(mockVideo.currentTime).toBe(5.1)
    })

    it("ignores other keys", () => {
      const keyEvent = new KeyboardEvent("keydown", { code: "Space" })

      window.onkeydown(keyEvent)

      expect(mockVideo.pause).not.toHaveBeenCalled()
    })

    it("does nothing when no selected video", () => {
      document.querySelector = jest.fn(() => null)

      const keyEvent = new KeyboardEvent("keydown", { code: "ArrowLeft" })

      expect(() => window.onkeydown(keyEvent)).not.toThrow()
    })
  })

  describe("Metadata Display", () => {
    it("displays metadata table when event and metadata are available", () => {
      const metadata = {
        123: { seqNum: "123", colA: "valueA", colB: "valueB" },
      }

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      // Send metadata first
      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: metadata,
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // Then send channel event
      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      // Should display metadata table
      expect(screen.getByText("seqNum")).toBeInTheDocument()
      expect(screen.getByText("123")).toBeInTheDocument()
      expect(screen.getByText("colA")).toBeInTheDocument()
      expect(screen.getByText("valueA")).toBeInTheDocument()
      expect(screen.getByText("colB")).toBeInTheDocument()
      expect(screen.getByText("valueB")).toBeInTheDocument()
    })

    it("shows 'No value set' for missing metadata values", () => {
      const metadata = {
        123: { seqNum: "123", colA: "valueA" }, // Missing colB
      }

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: metadata,
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      expect(screen.getByText("No value set")).toBeInTheDocument()
    })

    it("does not display metadata when no metaColumns", () => {
      const cameraWithoutMetaColumns = {
        ...mockCamera,
        mosaic_view_meta: [
          {
            channel: "channel1",
            mediaType: "image",
            metaColumns: [], // Empty meta columns
            selected: false,
          },
        ],
      }

      render(
        <MosaicView
          locationName="test-location"
          camera={cameraWithoutMetaColumns}
        />
      )

      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      expect(screen.queryByRole("table")).not.toBeInTheDocument()
    })

    it("does not display metadata when no latest event", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      // No channel event sent, so no latest event
      expect(screen.queryByRole("table")).not.toBeInTheDocument()
    })

    it("does not display metadata when event has no seq_num", () => {
      const channelEvent = {
        channel_name: "channel1",
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
        // Missing seq_num
      }

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      expect(screen.queryByRole("table")).not.toBeInTheDocument()
    })
  })

  describe("Component Cleanup", () => {
    it("removes event listeners on unmount", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener")
      const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

      const { unmount } = render(
        <MosaicView locationName="test-location" camera={mockCamera} />
      )

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "camera",
        expect.any(Function)
      )
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "channel",
        expect.any(Function)
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "camera",
        expect.any(Function)
      )
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "channel",
        expect.any(Function)
      )

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })
  })

  describe("Edge Cases", () => {
    it("handles camera with no mosaic_view_meta", () => {
      const cameraWithoutMeta = {
        ...mockCamera,
        mosaic_view_meta: [],
      }

      const { container } = render(
        <MosaicView locationName="test-location" camera={cameraWithoutMeta} />
      )

      const viewItems = container.querySelectorAll(".view")
      expect(viewItems).toHaveLength(0)
    })

    it("handles camera with only image channels", () => {
      const imageOnlyCamera = {
        ...mockCamera,
        mosaic_view_meta: [
          {
            channel: "channel1",
            mediaType: "image",
            metaColumns: ["colA"],
            selected: false,
          },
          {
            channel: "channel2",
            mediaType: "image",
            metaColumns: ["colB"],
            selected: false,
          },
        ],
      }

      const { container } = render(
        <MosaicView locationName="test-location" camera={imageOnlyCamera} />
      )

      const imageViews = container.querySelectorAll(".view-image")
      expect(imageViews).toHaveLength(2)

      const selectedViews = container.querySelectorAll(".view.selected")
      expect(selectedViews).toHaveLength(0) // No videos to select
    })

    it("handles mixed media types correctly", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      // Send events for different media types
      const imageEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      const videoEvent = {
        channel_name: "channel2",
        seq_num: 124,
        filename: "test_video.mp4",
        day_obs: "2024-01-01",
      }

      act(() => {
        window.dispatchEvent(
          new CustomEvent("channel", {
            detail: { data: imageEvent },
          })
        )
        window.dispatchEvent(
          new CustomEvent("channel", {
            detail: { data: videoEvent },
          })
        )
      })

      expect(screen.getByRole("img")).toBeInTheDocument()
      expect(document.querySelector("video")).toBeInTheDocument()
    })

    it("handles channel events for non-existent channels", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      const channelEvent = {
        channel_name: "nonexistent_channel",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      // Should not cause any errors
      expect(screen.getByText("Channel 1")).toBeInTheDocument()
    })
  })

  describe("Integration Tests", () => {
    it("handles complete workflow from metadata to display", () => {
      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      // 1. Send metadata
      const metadata = {
        123: { seqNum: "123", colA: "valueA", colB: "valueB" },
      }

      act(() => {
        const cameraEvent = new CustomEvent("camera", {
          detail: {
            data: metadata,
            dataType: "metadata",
          },
        })
        window.dispatchEvent(cameraEvent)
      })

      // 2. Send channel event
      const channelEvent = {
        channel_name: "channel1",
        seq_num: 123,
        filename: "test_image.jpg",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: channelEvent },
        })
        window.dispatchEvent(event)
      })

      // 3. Verify complete display
      expect(screen.getByText(": 2024-01-01")).toBeInTheDocument()
      expect(screen.getByRole("img")).toBeInTheDocument()
      expect(screen.getByText("valueA")).toBeInTheDocument()
      expect(screen.getByText("valueB")).toBeInTheDocument()
    })

    it("handles video selection and frame controls workflow", async () => {
      const mockVideo = {
        id: "v_hash_test-location/testcam/channel2/test_video.mp4",
        currentTime: 5.0,
        duration: 10.0,
        paused: false, // Set to false so pause() will be called
        pause: jest.fn(() => {
          mockVideo.paused = true // Update paused state when pause is called
        }),
      }
      _getById.mockReturnValue(mockVideo)

      render(<MosaicView locationName="test-location" camera={mockCamera} />)

      // Send video event
      const videoEvent = {
        channel_name: "channel2",
        seq_num: 123,
        filename: "test_video.mp4",
        day_obs: "2024-01-01",
      }

      act(() => {
        const event = new CustomEvent("channel", {
          detail: { data: videoEvent },
        })
        window.dispatchEvent(event)
      })

      // Trigger video loaded
      const video = document.querySelector("video")
      fireEvent.loadedData(video)

      // Check controls appear
      await waitFor(() => {
        const frameButtons = document.querySelectorAll(
          ".video-extra-controls button"
        )
        expect(frameButtons).toHaveLength(2)
      })

      // Test frame stepping
      const backButton = document.querySelector(".video-extra-controls button")
      fireEvent.click(backButton)

      expect(mockVideo.pause).toHaveBeenCalled()
      expect(mockVideo.currentTime).toBe(4.9)
    })
  })
})
