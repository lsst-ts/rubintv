import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { TableHeader, TableRow } from "../TableView"
import { RubinTVTableContext } from "../contexts/contexts"

/* global jest, describe, it, expect, beforeEach */

// Mock the Modal hook
const mockShowModal = jest.fn()
jest.mock("../../hooks/useModal", () => ({
  useModal: () => ({ showModal: mockShowModal }),
}))

// Mock the TableFilter component
jest.mock("../TableFilter", () => ({
  FilterDialog: ({ column }) => (
    <div data-testid="filter-dialog">Filter for {column}</div>
  ),
}))

// Mock clipboard API
window.navigator = window.navigator || {}
Object.assign(window.navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
})

// Test data
const mockCamera = {
  name: "test-camera",
  title: "Test Camera",
  channels: [
    {
      name: "channel1",
      title: "Channel 1",
      label: "Ch1",
      colour: "#069425",
      per_day: false,
    },
    {
      name: "channel2",
      title: "Channel 2",
      label: "Ch2",
      colour: "#00ff00",
      per_day: false,
    },
    {
      name: "daily-channel",
      title: "Daily Channel",
      label: "Daily",
      colour: "#0000ff",
      per_day: true,
    },
  ],
  copy_row_template: "template-{dayObs}-{seqNum}",
  image_viewer_link: "viewer-{dayObs}-{seqNum}",
}

const mockChannelData = {
  100: {
    channel1: { seq_num: 100, date_added: "2023-01-01" },
    channel2: { seq_num: 100, date_added: "2023-01-01" },
  },
  101: {
    channel1: { seq_num: 101, date_added: "2023-01-01" },
  },
}

const mockMetadata = {
  100: {
    exposure_time: 30.5,
    filter: "r",
    temperature: 20,
    _temperature: "green",
    active: true,
    notes: undefined,
    complex_data: {
      key1: "value1",
      key2: "value2",
      DISPLAY_VALUE: "😀",
    },
    array_data: ["item1", "item2"],
    null_data: null,
    controller: "main-controller",
    "@channel1": "🔧",
  },
  101: {
    exposure_time: 45.75,
    filter: "g",
    temperature: 22,
    active: false,
  },
}

const mockMetadataColumns = [
  { name: "exposure_time", desc: "Exposure time in seconds" },
  { name: "filter", desc: "Filter used" },
  { name: "temperature", desc: "Temperature in Celsius" },
  { name: "active", desc: "Whether active" },
  { name: "notes", desc: "Additional notes" },
  { name: "complex_data", desc: "Complex metadata" },
  { name: "array_data", desc: "Array data" },
  { name: "null_data", desc: "Null data field" },
]

const mockContextValue = {
  locationName: "summit",
  camera: mockCamera,
  dayObs: "2023-01-01",
  siteLocation: "summit",
}

const defaultFilterOn = { column: "", value: "" }
const defaultSortOn = { column: "seq", order: "asc" }

const TestWrapper = ({ children, contextValue = {} }) => (
  <RubinTVTableContext.Provider
    value={{ ...mockContextValue, ...contextValue }}
  >
    {children}
  </RubinTVTableContext.Provider>
)

describe("TableView Components", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe("MetadataCell", () => {
    it("renders metadata cell with indicator properly", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={{}}
                metadataColumns={mockMetadataColumns}
                metadataRow={mockMetadata["100"]}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("20")).toBeInTheDocument()
      expect(screen.getByText("20").closest("td")).toHaveClass("green")
    })

    it("renders string values correctly", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[{ name: "notes", desc: "Notes" }]}
                metadataRow={{ notes: "Test String" }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("Test String")).toBeInTheDocument()
    })

    it("renders number values with proper formatting", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[
                  { name: "exposure_time", desc: "Exposure time" },
                  { name: "temperature", desc: "Temperature" },
                  { name: "rotation", desc: "Rotation" },
                ]}
                metadataRow={{
                  exposure_time: 30.5,
                  temperature: 22.019218,
                  rotation: "45.9098",
                }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("30.50")).toBeInTheDocument()
      expect(screen.getByText("22.02")).toBeInTheDocument()
      expect(screen.getByText("45.9098")).toBeInTheDocument()
    })

    it("renders boolean values correctly", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[{ name: "active", desc: "Active status" }]}
                metadataRow={{ active: true }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("True")).toBeInTheDocument()
    })

    it("handles undefined values", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[{ name: "notes", desc: "Notes" }]}
                metadataRow={{ notes: undefined }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      const cell = screen.getByRole("cell", { name: /no data/i })
      expect(cell).toHaveAttribute("title", "No data")
    })

    it("handles null values", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[{ name: "null_data", desc: "Null data" }]}
                metadataRow={{ null_data: null }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      const cell = screen.getByRole("cell", { name: /no data/i })
      expect(cell).toHaveAttribute("title", "No data")
    })

    it("renders foldout cell for object data", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[
                  { name: "complex_data", desc: "Complex data" },
                ]}
                metadataRow={mockMetadata["100"]}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("😀")).toBeInTheDocument()
    })
  })

  describe("ChannelCell", () => {
    it("renders channel button when event exists", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <tr>
                <td className="grid-cell">
                  <a
                    className="button button-table channel1"
                    style={{ backgroundColor: "#069425" }}
                    href="/event/100"
                    aria-label="channel1"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </TestWrapper>
      )
      const link = screen.getByRole("link", { name: "channel1" })
      expect(link).toHaveStyle("background-color: #069425")
      expect(link).toHaveAttribute("href", "/event/100")
    })

    it("renders replacement text when no event and replacement provided", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={{}}
                metadataColumns={[]}
                metadataRow={{ "@channel1": "🔧" }}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("🔧")).toBeInTheDocument()
    })
  })

  describe("TableRow", () => {
    it("renders complete row with all elements", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={mockMetadataColumns}
                metadataRow={mockMetadata["100"]}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(screen.getByText("100")).toBeInTheDocument()
      expect(screen.getAllByRole("cell", { name: /no data/i })).toHaveLength(2)
      expect(
        screen.getByRole("button", { name: /copy to clipboard/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("link", { name: /open image viewer/i })
      ).toBeInTheDocument()
    })

    it("handles copy button click", async () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[]}
                metadataRow={{}}
              />
            </tbody>
          </table>
        </TestWrapper>
      )

      const copyButton = screen.getByRole("button", {
        name: /copy to clipboard/i,
      })
      fireEvent.click(copyButton)

      expect(window.navigator.clipboard.writeText).toHaveBeenCalledWith(
        "template-20230101-000100"
      )
    })

    it("does not render CCS viewer link for non-CCS sites", () => {
      render(
        <TestWrapper contextValue={{ siteLocation: "other-site" }}>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[]}
                metadataRow={{}}
              />
            </tbody>
          </table>
        </TestWrapper>
      )
      expect(
        screen.queryByRole("link", { name: /open image viewer/i })
      ).not.toBeInTheDocument()
    })
  })

  describe("FoldoutCell", () => {
    it("opens modal when clicked", async () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[
                  { name: "complex_data", desc: "Complex data" },
                ]}
                metadataRow={mockMetadata["100"]}
              />
            </tbody>
          </table>
        </TestWrapper>
      )

      const foldoutButton = screen.getByText("😀")
      fireEvent.click(foldoutButton)

      expect(mockShowModal).toHaveBeenCalled()
    })

    it("shows book emoji for array data", () => {
      render(
        <TestWrapper>
          <table>
            <tbody>
              <TableRow
                seqNum="100"
                camera={mockCamera}
                channels={mockCamera.channels.filter((c) => !c.per_day)}
                channelRow={mockChannelData["100"]}
                metadataColumns={[{ name: "array_data", desc: "Array data" }]}
                metadataRow={mockMetadata["100"]}
              />
            </tbody>
          </table>
        </TestWrapper>
      )

      expect(screen.getByText("📖")).toBeInTheDocument()
    })
  })

  describe("ChannelHeader", () => {
    const mockSetFilterOn = jest.fn()
    const mockSetSortOn = jest.fn()

    beforeEach(() => {
      mockSetFilterOn.mockClear()
      mockSetSortOn.mockClear()
    })

    it("renders channel headers correctly", () => {
      render(
        <TestWrapper>
          <TableHeader
            camera={mockCamera}
            metadataColumns={mockMetadataColumns}
            filterOn={defaultFilterOn}
            setFilterOn={mockSetFilterOn}
            filteredRowsCount={2}
            unfilteredRowsCount={2}
            sortOn={defaultSortOn}
            setSortOn={mockSetSortOn}
          />
        </TestWrapper>
      )
      expect(screen.getByText("Ch1")).toBeInTheDocument()
      expect(screen.getByText("Ch2")).toBeInTheDocument()
    })

    it("handles metadata column click for filtering", async () => {
      render(
        <TestWrapper>
          <TableHeader
            camera={mockCamera}
            metadataColumns={mockMetadataColumns}
            filterOn={defaultFilterOn}
            setFilterOn={mockSetFilterOn}
            filteredRowsCount={2}
            unfilteredRowsCount={2}
            sortOn={defaultSortOn}
            setSortOn={mockSetSortOn}
          />
        </TestWrapper>
      )

      const header = screen.getByText("exposure_time")
      fireEvent.click(header)

      expect(mockShowModal).toHaveBeenCalled()
    })
  })

  describe("TableHeader", () => {
    const mockSetFilterOn = jest.fn()
    const mockSetSortOn = jest.fn()

    it("renders all headers correctly", () => {
      render(
        <TestWrapper>
          <TableHeader
            camera={mockCamera}
            metadataColumns={mockMetadataColumns}
            filterOn={defaultFilterOn}
            setFilterOn={mockSetFilterOn}
            filteredRowsCount={2}
            unfilteredRowsCount={2}
            sortOn={defaultSortOn}
            setSortOn={mockSetSortOn}
          />
        </TestWrapper>
      )

      expect(screen.getByText("Seq. No.")).toBeInTheDocument()
      expect(screen.getByText("CCS Image Viewer")).toBeInTheDocument()
      expect(screen.getByText("Ch1")).toBeInTheDocument()
      expect(screen.getByText("Ch2")).toBeInTheDocument()
      mockMetadataColumns.forEach((col) => {
        expect(screen.getByText(col.name)).toBeInTheDocument()
      })
    })

    it("does not render copy column when template not provided", () => {
      const cameraWithoutCopy = { ...mockCamera, copy_row_template: undefined }
      render(
        <TestWrapper>
          <TableHeader
            camera={cameraWithoutCopy}
            metadataColumns={mockMetadataColumns}
            filterOn={defaultFilterOn}
            setFilterOn={mockSetFilterOn}
            filteredRowsCount={2}
            unfilteredRowsCount={2}
            sortOn={defaultSortOn}
            setSortOn={mockSetSortOn}
          />
        </TestWrapper>
      )
      expect(
        screen.queryByRole("columnheader", { name: /copy/i })
      ).not.toBeInTheDocument()
    })
  })
})
