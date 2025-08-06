/* eslint-disable react/prop-types */
import "@testing-library/jest-dom"
import React from "react"
import { render, screen, act } from "@testing-library/react"
import MediaDisplay from "../MediaDisplay"
import {
  getDocumentLocation,
  getMediaType,
  getMediaProxyUrl,
} from "../../modules/utils"

/* global jest, describe, it, expect, beforeEach, afterEach */

// Mock utility functions
jest.mock("../../modules/utils", () => ({
  getBaseFromEventUrl: jest.fn((url) => url.replace(/\/[^/]*$/, "/")),
  getMediaType: jest.fn((ext) => (ext === "mp4" ? "video" : "image")),
  getMediaProxyUrl: jest.fn(
    (mediaType, locationName, cameraName, channelName, filename) =>
      `http://proxy.test/${mediaType}/${locationName}/${cameraName}/${channelName}/${filename}`
  ),
  getCameraPageForDateUrl: jest.fn(
    (locationName, cameraName, dayObs) =>
      `http://test.com/${locationName}/${cameraName}/${dayObs}`
  ),
  getDocumentLocation: jest.fn(
    () => "http://test.com/test-location/testcam/channel1/current"
  ),
}))

// Mock Clock components
jest.mock("../Clock", () => ({
  TimeSinceLastImageClock: ({ camera }) => (
    <div data-testid="time-since-clock">
      Mock TimeSinceLastImageClock - {camera.name}
    </div>
  ),
}))

// Mock PrevNext component
jest.mock("../PrevNext", () => ({
  __esModule: true,
  default: ({ initialPrevNext }) => (
    <div data-testid="prev-next">
      Mock PrevNext - {initialPrevNext.prev?.seq_num || "none"} |{" "}
      {initialPrevNext.next?.seq_num || "none"}
    </div>
  ),
}))

describe("MediaDisplay Component", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [
      {
        name: "channel1",
        title: "Channel 1",
        colour: "#ff0000",
        text_colour: "#ffffff",
      },
      {
        name: "channel2",
        title: "Channel 2",
        colour: "#00ff00",
        text_colour: "#000000",
      },
    ],
    time_since_clock: { label: "Since last image:" },
    metadata_columns: {},
  }

  const mockImageEvent = {
    key: "test/key",
    hash: "testhash",
    camera_name: "testcam",
    day_obs: "2024-01-01",
    channel_name: "channel1",
    seq_num: 12345,
    filename: "test_image.jpg",
    ext: "jpg",
  }

  const mockVideoEvent = {
    ...mockImageEvent,
    filename: "test_video.mp4",
    ext: "mp4",
  }

  const mockPrevNext = {
    prev: { seq_num: 12344 },
    next: { seq_num: 12346 },
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  afterEach(() => {})

  describe("Component Rendering", () => {
    it("renders null when no initEvent is provided", () => {
      const { container } = render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={null}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it("renders image event correctly", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      // Check event info
      expect(screen.getByText("2024-01-01")).toBeInTheDocument()
      expect(screen.getByText("12345")).toBeInTheDocument()

      // Check PrevNext component
      expect(screen.getByTestId("prev-next")).toBeInTheDocument()

      // Check image element
      const img = screen.getByRole("img")
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute("id", "eventImage")

      // Check filename description
      expect(screen.getByText("test_image.jpg")).toBeInTheDocument()

      // Check other channel links
      expect(screen.getByText("Channel 1")).toBeInTheDocument()
      expect(screen.getByText("Channel 2")).toBeInTheDocument()
    })

    it("renders video event correctly", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockVideoEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      // Check video element instead of image
      const video = document.querySelector("video")
      expect(video).toBeInTheDocument()
      expect(video).toHaveAttribute("id", "eventVideo")
      expect(video).toHaveAttribute("controls")

      // Check filename description
      expect(screen.getByText("test_video.mp4")).toBeInTheDocument()
    })

    it("renders TimeSinceLastImageClock when isCurrent is true and camera has time_since_clock", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={true}
        />
      )

      expect(screen.getByTestId("time-since-clock")).toBeInTheDocument()
    })

    it("does not render TimeSinceLastImageClock when isCurrent is false", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      expect(screen.queryByTestId("time-since-clock")).not.toBeInTheDocument()
    })

    it("does not render TimeSinceLastImageClock when camera has no time_since_clock", () => {
      const cameraWithoutClock = {
        ...mockCamera,
        time_since_clock: undefined,
      }

      render(
        <MediaDisplay
          locationName="test-location"
          camera={cameraWithoutClock}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={true}
        />
      )

      expect(screen.queryByTestId("time-since-clock")).not.toBeInTheDocument()
    })
  })

  describe("Event Handling", () => {
    it("updates media event when channel event is received", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      // Initial state
      expect(screen.getByText("12345")).toBeInTheDocument()

      // Dispatch new event
      const newEvent = {
        ...mockImageEvent,
        seq_num: 99999,
        filename: "new_image.png",
        ext: "png",
      }

      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            data: newEvent,
            dataType: "event",
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Check updated content
      expect(screen.getByText("99999")).toBeInTheDocument()
      expect(screen.getByText("new_image.png")).toBeInTheDocument()
    })

    it("ignores non-event channel messages", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      // Initial state
      expect(screen.getByText("12345")).toBeInTheDocument()

      // Dispatch non-event message
      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            data: { some: "data" },
            dataType: "metadata",
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Should not change
      expect(screen.getByText("12345")).toBeInTheDocument()
    })

    it("ignores channel events with no data", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      // Initial state
      expect(screen.getByText("12345")).toBeInTheDocument()

      // Dispatch event with no data
      act(() => {
        const channelEvent = new CustomEvent("channel", {
          detail: {
            data: null,
            dataType: "event",
          },
        })
        window.dispatchEvent(channelEvent)
      })

      // Should not change
      expect(screen.getByText("12345")).toBeInTheDocument()
    })
  })

  describe("URL Generation", () => {
    it("generates correct date URL", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      const dateLink = screen.getByText("2024-01-01")
      expect(dateLink).toHaveAttribute(
        "href",
        "http://test.com/test-location/testcam/2024-01-01"
      )
    })

    it("generates correct media source URL", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      const img = screen.getByRole("img")
      expect(img).toHaveAttribute(
        "src",
        "http://proxy.test/image/test-location/testcam/channel1/test_image.jpg"
      )
    })
  })

  describe("Link Properties", () => {
    it("sets correct link properties for media display", () => {
      render(
        <MediaDisplay
          locationName="test-location"
          camera={mockCamera}
          initEvent={mockImageEvent}
          prevNext={mockPrevNext}
          allChannelNames={["channel1", "channel2"]}
          isCurrent={false}
        />
      )

      const eventLink = document.querySelector(".event-link")
      expect(eventLink).toHaveAttribute("target", "_blank")
      expect(eventLink).toHaveAttribute("rel", "noopener noreferrer")
    })
  })
})

describe("OtherChannelLinks Component", () => {
  const mockCamera = {
    name: "testcam",
    title: "Test Camera",
    channels: [
      {
        name: "channel1",
        title: "Channel 1",
        colour: "#ff0000",
        text_colour: "#ffffff",
      },
      {
        name: "channel2",
        title: "Channel 2",
        colour: "#00ff00",
        text_colour: "#000000",
      },
      {
        name: "channel3",
        title: "Channel 3",
        colour: "#0000ff",
        text_colour: "#ffffff",
      },
    ],
    metadata_columns: {},
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders channel links with correct styles", () => {
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    const channel1Link = screen.getByText("Channel 1")
    expect(channel1Link).toHaveStyle({
      backgroundColor: "#ff0000",
      color: "#ffffff",
    })

    const channel2Link = screen.getByText("Channel 2")
    expect(channel2Link).toHaveStyle({
      backgroundColor: "#00ff00",
      color: "#000000",
    })

    // Channel 3 should not be rendered since it's not in allChannelNames
    expect(screen.queryByText("Channel 3")).not.toBeInTheDocument()
  })

  it("builds correct URLs for current channel links", () => {
    getDocumentLocation.mockReturnValue(
      "http://test.com/test-location/testcam/channel1/current"
    )
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    const channel2Link = screen.getByText("Channel 2")
    expect(channel2Link).toHaveAttribute(
      "href",
      "http://test.com/test-location/testcam/channel2/current"
    )
  })

  it("builds correct URLs for query parameter links", () => {
    getDocumentLocation.mockReturnValue(
      "http://test.com/page?channel_name=channel1&other=param"
    )
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    const channel2Link = screen.getByText("Channel 2")
    expect(channel2Link).toHaveAttribute(
      "href",
      "http://test.com/page?channel_name=channel2&other=param"
    )
  })

  it("updates channel names when channel event is received", () => {
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    // Initially only channel1 and channel2 are visible
    expect(screen.getByText("Channel 1")).toBeInTheDocument()
    expect(screen.getByText("Channel 2")).toBeInTheDocument()
    expect(screen.queryByText("Channel 3")).not.toBeInTheDocument()

    // Dispatch channel event with updated channel names
    act(() => {
      const channelEvent = new CustomEvent("channel", {
        detail: {
          data: ["channel1", "channel2", "channel3"],
        },
      })
      window.dispatchEvent(channelEvent)
    })

    // Now channel3 should be visible
    expect(screen.getByText("Channel 3")).toBeInTheDocument()
  })

  it("ignores invalid channel name updates", () => {
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    // Dispatch invalid channel event
    act(() => {
      const channelEvent = new CustomEvent("channel", {
        detail: {
          data: null, // Invalid data
        },
      })
      window.dispatchEvent(channelEvent)
    })

    // Should still show original channels
    expect(screen.getByText("Channel 1")).toBeInTheDocument()
    expect(screen.getByText("Channel 2")).toBeInTheDocument()

    // Dispatch non-array data
    act(() => {
      const channelEvent = new CustomEvent("channel", {
        detail: {
          data: "not an array",
        },
      })
      window.dispatchEvent(channelEvent)
    })

    // Should still show original channels
    expect(screen.getByText("Channel 1")).toBeInTheDocument()
    expect(screen.getByText("Channel 2")).toBeInTheDocument()
  })

  it("ignores empty channel name arrays", () => {
    render(
      <MediaDisplay
        locationName="test-location"
        camera={mockCamera}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={["channel1", "channel2"]}
        isCurrent={false}
      />
    )

    // Dispatch empty array
    act(() => {
      const channelEvent = new CustomEvent("channel", {
        detail: {
          data: [],
        },
      })
      window.dispatchEvent(channelEvent)
    })

    // Should still show original channels
    expect(screen.getByText("Channel 1")).toBeInTheDocument()
    expect(screen.getByText("Channel 2")).toBeInTheDocument()
  })
})

describe("Media Event Bundling", () => {
  it("correctly bundles image events", () => {
    const imageEvent = {
      key: "test/key",
      hash: "testhash",
      camera_name: "testcam",
      day_obs: "2024-01-01",
      channel_name: "channel1",
      seq_num: 12345,
      filename: "test_image.jpg",
      ext: "jpg",
    }

    render(
      <MediaDisplay
        locationName="test-location"
        camera={{
          name: "testcam",
          channels: [],
          metadata_columns: {},
          title: "Test",
        }}
        initEvent={imageEvent}
        prevNext={{ prev: null, next: null }}
        allChannelNames={[]}
        isCurrent={false}
      />
    )

    expect(getMediaType).toHaveBeenCalledWith("jpg")
    expect(getMediaProxyUrl).toHaveBeenCalledWith(
      "image",
      "test-location",
      "testcam",
      "channel1",
      "test_image.jpg"
    )
  })

  it("correctly bundles video events", () => {
    const videoEvent = {
      key: "test/key",
      hash: "testhash",
      camera_name: "testcam",
      day_obs: "2024-01-01",
      channel_name: "channel1",
      seq_num: 12345,
      filename: "test_video.mp4",
      ext: "mp4",
    }

    render(
      <MediaDisplay
        locationName="test-location"
        camera={{
          name: "testcam",
          channels: [],
          metadata_columns: {},
          title: "Test",
        }}
        initEvent={videoEvent}
        prevNext={{ prev: null, next: null }}
        allChannelNames={[]}
        isCurrent={false}
      />
    )

    expect(getMediaType).toHaveBeenCalledWith("mp4")
    expect(getMediaProxyUrl).toHaveBeenCalledWith(
      "video",
      "test-location",
      "testcam",
      "channel1",
      "test_video.mp4"
    )
  })
})

describe("Component Cleanup", () => {
  it("removes event listeners on unmount", () => {
    const addEventListenerSpy = jest.spyOn(window, "addEventListener")
    const removeEventListenerSpy = jest.spyOn(window, "removeEventListener")

    const { unmount } = render(
      <MediaDisplay
        locationName="test-location"
        camera={{
          name: "testcam",
          channels: [],
          metadata_columns: {},
          title: "Test",
        }}
        initEvent={{
          key: "test/key",
          hash: "testhash",
          camera_name: "testcam",
          day_obs: "2024-01-01",
          channel_name: "channel1",
          seq_num: 12345,
          filename: "test_image.jpg",
          ext: "jpg",
        }}
        prevNext={{ prev: null, next: null }}
        allChannelNames={[]}
        isCurrent={false}
      />
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
})
