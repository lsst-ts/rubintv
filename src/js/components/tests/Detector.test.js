/* global global */
import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"
import DetectorStatusVisualization, {
  Cells,
  Cell,
  ResetButton,
  OtherQueuesSection,
  DetectorCanvas,
} from "../Detector"

import { simplePost } from "../../modules/utils"
import { ModalProvider } from "../Modal"
import {
  /* eslint-env jest */
  getStatusClass,
  getStatusColor,
  createPlaceholders,
} from "../../modules/detectorUtils"
import { RedisEndpointContext, useRedisEndpoint } from "../contexts/contexts"
import "jest-canvas-mock"

/* global jest, describe, it, expect, beforeEach, beforeAll */

// Mock external dependencies
jest.mock("../../modules/utils", () => ({
  simplePost: jest.fn(),
}))

jest.mock("../../modules/detectorUtils", () => ({
  RESET_PREFIX: "RUBINTV_CONTROL_RESET_",
  getStatusClass: jest.fn((status) => `status-${status}`),
  getStatusColor: jest.fn((status) => `#${status}`),
  createPlaceholders: jest.fn((count) => {
    const placeholders = {}
    for (let i = 0; i < count; i++) {
      placeholders[i] = { status: "missing", queue_length: 0 }
    }
    return { workers: placeholders, numWorkers: count }
  }),
}))

jest.mock("../Modal", () => ({
  ModalProvider: ({ children }) => (
    <div data-testid="modal-provider">{children}</div>
  ),
  ConfirmationModal: ({ title, message, onConfirm, onCancel }) => (
    <div data-testid="confirmation-modal">
      <h2>{title}</h2>
      <p>{message}</p>
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}))

const mockShowModal = jest.fn()
const mockCloseModal = jest.fn()

const mockUseModal = jest.fn(() => ({
  modalContent: null,
  showModal: mockShowModal,
  closeModal: mockCloseModal,
}))

jest.mock("../../hooks/useModal", () => ({
  useModal: (...args) => mockUseModal(...args),
}))

// Mock detector maps
jest.mock("../../data/detectorMap.json", () => ({
  0: {
    corners: {
      upperLeft: [0, 0],
      upperRight: [10, 0],
      lowerLeft: [0, 10],
      lowerRight: [10, 10],
    },
  },
}))

jest.mock("../../data/cwfsMap.json", () => ({
  0: {
    corners: {
      upperLeft: [0, 0],
      upperRight: [5, 0],
      lowerLeft: [0, 5],
      lowerRight: [5, 5],
    },
  },
}))

beforeAll(() => {
  // Mock ResizeObserver to trigger dimensions update
  global.ResizeObserver = jest.fn().mockImplementation((callback) => ({
    observe: jest.fn((element) => {
      // Trigger the callback immediately to simulate resize
      setTimeout(() => callback([{ target: element }]), 0)
    }),
    disconnect: jest.fn(),
  }))

  // Mock getBoundingClientRect to return realistic dimensions
  Element.prototype.getBoundingClientRect = jest.fn(() => ({
    width: 400,
    height: 400,
    top: 0,
    left: 0,
    bottom: 400,
    right: 400,
    x: 0,
    y: 0,
    toJSON: () => {},
  }))

  // Mock window.devicePixelRatio
  Object.defineProperty(window, "devicePixelRatio", {
    value: 1,
    writable: true,
  })
})

describe("Detector Components", () => {
  const mockDetectorKeys = [
    { name: "sfmSet0", key: "CLUSTER_STATUS_SFM_SET_0" },
    { name: "spareWorkers", key: "CLUSTER_STATUS_SPARE_WORKERS" },
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe("DetectorStatusVisualization", () => {
    it("renders the main detector visualization with legend and sections", () => {
      render(
        <RedisEndpointContext.Provider
          value={{ url: "http://test.com", admin: true }}
        >
          <DetectorStatusVisualization
            detectorKeys={mockDetectorKeys}
            redisEndpointUrl="http://test.com"
            admin={true}
          />
        </RedisEndpointContext.Provider>
      )

      expect(screen.getByText("Free")).toBeInTheDocument()
      expect(screen.getByText("Busy")).toBeInTheDocument()
      expect(screen.getByText("Queued")).toBeInTheDocument()
      expect(screen.getByText("Imaging Worker Set 1")).toBeInTheDocument()
      expect(screen.getByText("Backlog Workers")).toBeInTheDocument()
      expect(screen.getByText("Other Queues")).toBeInTheDocument()
    })

    it("handles detector status events correctly", async () => {
      render(
        <RedisEndpointContext.Provider
          value={{ url: "http://test.com", admin: true }}
        >
          <DetectorStatusVisualization
            detectorKeys={mockDetectorKeys}
            redisEndpointUrl="http://test.com"
            admin={true}
          />
        </RedisEndpointContext.Provider>
      )

      const mockEventData = {
        aosStep1b: { workers: { 0: { status: "queued", queue_length: 0 } } },
        spareWorkers: { workers: { 0: { status: "free" } } },
      }

      const event = new CustomEvent("detectors", {
        detail: {
          dataType: "detectorStatus",
          data: mockEventData,
        },
      })

      act(() => {
        fireEvent(window, event)
      })

      // Component should update with new status data
      await waitFor(() => {
        expect(getStatusClass).toHaveBeenCalledWith("queued")
        expect(getStatusClass).toHaveBeenCalledWith("free")
      })
    })

    it("ignores non-detector status events", () => {
      const consoleSpy = jest.spyOn(console, "log").mockImplementation()

      render(
        <RedisEndpointContext.Provider
          value={{ url: "http://test.com", admin: true }}
        >
          <DetectorStatusVisualization
            detectorKeys={mockDetectorKeys}
            redisEndpointUrl="http://test.com"
            admin={true}
          />
        </RedisEndpointContext.Provider>
      )

      const event = new CustomEvent("detectors", {
        detail: {
          dataType: "otherData",
          data: {},
        },
      })

      fireEvent(window, event)

      expect(consoleSpy).not.toHaveBeenCalled()
      consoleSpy.mockRestore()
    })
  })

  describe("Cell Component", () => {
    it("renders basic cell with status class", () => {
      const { container } = render(
        <div>
          <Cell status={{ status: "free", queue_length: 0 }} />
        </div>
      )

      const cell = container.querySelector(".detector-cell")
      expect(cell).toHaveClass("status-free")
      expect(getStatusClass).toHaveBeenCalledWith("free")
    })

    it("displays queue length for queued status", () => {
      render(
        <div>
          <Cell status={{ status: "queued", queue_length: 5 }} />
        </div>
      )

      expect(screen.getByText("5")).toBeInTheDocument()
      expect(screen.getByText("5")).toHaveClass("queue-length")
    })

    it("does not display queue length for non-queued status", () => {
      const { container } = render(
        <div>
          <Cell status={{ status: "busy", queue_length: 3 }} />
        </div>
      )

      expect(screen.queryByText("3")).not.toBeInTheDocument()
      expect(container.querySelector(".queue-length")).not.toBeInTheDocument()
    })
  })

  describe("ResetButton Component", () => {
    it("renders reset button for admin users", () => {
      render(
        <RedisEndpointContext.Provider
          value={{ url: "http://test.com", admin: true }}
        >
          <ResetButton redisKey="CLUSTER_STATUS_TEST" />
        </RedisEndpointContext.Provider>
      )

      expect(screen.getByText("Restart Workers")).toBeInTheDocument()
    })

    it("does not render for non-admin users", () => {
      const { container } = render(
        <RedisEndpointContext.Provider
          value={{ url: "http://test.com", admin: false }}
        >
          <ResetButton redisKey="CLUSTER_STATUS_TEST" />
        </RedisEndpointContext.Provider>
      )

      expect(container.firstChild).toBeNull()
    })

    it("handles reset action successfully", async () => {
      const mockSimplePost = simplePost
      mockSimplePost.mockResolvedValue(true)

      // Create a mock confirmation modal that actually renders and can be interacted with
      let modalContent = null
      const testShowModal = jest.fn((content) => {
        modalContent = content
      })
      const testCloseModal = jest.fn(() => {
        modalContent = null
      })

      // Override the mock for this test
      mockUseModal.mockReturnValue({
        modalContent,
        showModal: testShowModal,
        closeModal: testCloseModal,
      })

      const { rerender } = render(
        <ModalProvider>
          <RedisEndpointContext.Provider
            value={{ url: "http://test.com", admin: true }}
          >
            <ResetButton redisKey="CLUSTER_STATUS_TEST" />
            {/* Render the modal content if it exists */}
            {modalContent}
          </RedisEndpointContext.Provider>
        </ModalProvider>
      )

      // Click reset button
      fireEvent.click(screen.getByText(/restart workers/i))

      // Verify modal was shown
      expect(testShowModal).toHaveBeenCalled()

      // Re-render to show the modal content
      rerender(
        <ModalProvider>
          <RedisEndpointContext.Provider
            value={{ url: "http://test.com", admin: true }}
          >
            <ResetButton redisKey="CLUSTER_STATUS_TEST" />
            {modalContent}
          </RedisEndpointContext.Provider>
        </ModalProvider>
      )

      // Find and click the confirm button in the modal
      const confirmButton = screen.getByText("Confirm")
      fireEvent.click(confirmButton)

      // Wait for the API call to be made
      await waitFor(() => {
        expect(mockSimplePost).toHaveBeenCalledWith("http://test.com", {
          key: "RUBINTV_CONTROL_RESET_TEST",
          value: "reset",
        })
      })
    })
  })

  describe("OtherQueuesSection Component", () => {
    it("renders queue table with data", () => {
      const mockQueues = {
        text: {
          queue1: "5",
          queue2: "10",
          queue3: "",
        },
      }

      render(<OtherQueuesSection otherQueues={mockQueues} />)

      expect(screen.getByText("Other Queues")).toBeInTheDocument()
      expect(screen.getByText("queue1")).toBeInTheDocument()
      expect(screen.getByText("5")).toBeInTheDocument()
      expect(screen.getByText("queue2")).toBeInTheDocument()
      expect(screen.getByText("10")).toBeInTheDocument()
      expect(screen.queryByText("queue3")).not.toBeInTheDocument()
    })

    it("handles empty queue data", () => {
      const mockQueues = { text: {} }

      render(<OtherQueuesSection otherQueues={mockQueues} />)

      expect(screen.getByText("Other Queues")).toBeInTheDocument()
      const tbody = screen.getByRole("table").querySelector("tbody")
      expect(tbody?.children).toHaveLength(0)
    })
  })

  describe("DetectorCanvas Component", () => {
    it("renders canvas element and draws on it", async () => {
      const mockStatuses = {
        workers: { 0: { status: "free", queue_length: 0 } },
        numWorkers: 1,
      }

      // Mock a more realistic ResizeObserver that sets dimensions
      global.ResizeObserver = jest.fn().mockImplementation((callback) => {
        return {
          observe: jest.fn((element) => {
            // Immediately trigger with proper dimensions
            const entries = [
              {
                target: element,
                contentRect: { width: 400, height: 400 },
              },
            ]
            callback(entries)
          }),
          disconnect: jest.fn(),
        }
      })

      render(
        <DetectorCanvas
          detectorMap={{
            0: {
              corners: {
                upperLeft: [0, 0],
                upperRight: [10, 0],
                lowerLeft: [0, 10],
                lowerRight: [10, 10],
              },
            },
          }}
          detectorStatuses={mockStatuses}
        />
      )

      // Wait for both ResizeObserver and canvas drawing effects to complete
      await waitFor(() => {
        const canvas = document.querySelector("canvas")
        expect(canvas).toBeInTheDocument()
      })

      await waitFor(
        () => {
          const canvas = document.querySelector("canvas")
          const ctx = canvas.getContext("2d")
          expect(ctx.clearRect).toHaveBeenCalled()
          expect(ctx.beginPath).toHaveBeenCalled()
          expect(ctx.moveTo).toHaveBeenCalled()
          expect(ctx.fill).toHaveBeenCalled()
        },
        { timeout: 1000 }
      )
    })

    it("updates canvas when statuses change", async () => {
      const mockStatuses = {
        workers: { 0: { status: "queued", queue_length: 3 } },
        numWorkers: 1,
      }

      const { rerender } = render(
        <DetectorCanvas
          detectorMap={{
            0: {
              corners: {
                upperLeft: [0, 0],
                upperRight: [10, 0],
                lowerLeft: [0, 10],
                lowerRight: [10, 10],
              },
            },
          }}
          detectorStatuses={mockStatuses}
        />
      )

      await waitFor(() => {
        expect(getStatusColor).toHaveBeenCalledWith("queued")
      })

      // Update status and rerender
      const newStatuses = {
        workers: { 0: { status: "busy", queue_length: 0 } },
        numWorkers: 1,
      }

      rerender(
        <DetectorCanvas
          detectorMap={{
            0: {
              corners: {
                upperLeft: [0, 0],
                upperRight: [10, 0],
                lowerLeft: [0, 10],
                lowerRight: [10, 10],
              },
            },
          }}
          detectorStatuses={newStatuses}
        />
      )

      await waitFor(() => {
        expect(getStatusColor).toHaveBeenCalledWith("busy")
      })
    })
  })

  describe("useRedisEndpoint Hook", () => {
    const TestComponent = () => {
      const { url, admin } = useRedisEndpoint()
      return (
        <div>
          <span>URL: {url}</span>
          <span>Admin: {admin.toString()}</span>
        </div>
      )
    }

    it("throws error when used outside provider", () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation()
      expect(() => render(<TestComponent />)).toThrow(
        "useRedisEndpoint must be used within a RedisEndpointProvider"
      )

      consoleSpy.mockRestore()
    })
  })

  describe("Cells Component", () => {
    it("renders cells with placeholder workers", () => {
      const mockStatuses = {
        workers: { 0: { status: "busy", queue_length: 0 } },
        numWorkers: 3,
      }

      createPlaceholders.mockReturnValue({
        workers: {
          0: { status: "missing", queue_length: 0 },
          1: { status: "missing", queue_length: 0 },
          2: { status: "missing", queue_length: 0 },
        },
        numWorkers: 3,
      })

      const { container } = render(
        <Cells statuses={mockStatuses} prefix="test" />
      )

      expect(createPlaceholders).toHaveBeenCalledWith(3)
      expect(container.querySelectorAll(".detector-cell")).toHaveLength(3)
    })

    it("renders cells without placeholders when numWorkers is 0", () => {
      const mockStatuses = {
        workers: { 0: { status: "free", queue_length: 0 } },
        numWorkers: 0,
      }

      const { container } = render(
        <Cells statuses={mockStatuses} prefix="test" />
      )

      expect(createPlaceholders).not.toHaveBeenCalled()
      expect(container.querySelectorAll(".detector-cell")).toHaveLength(1)
    })
  })
})
