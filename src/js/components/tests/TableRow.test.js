/* eslint-env jest */
import "@testing-library/jest-dom" // Import jest-dom for custom matchers
import React from "react"
import { render, screen } from "@testing-library/react"
import { TableRow } from "../TableView"
import { RubinTVTableContext } from "../componentTypes" // or wherever it's exported
import { indicatorForAttr, replaceInString } from "../../modules/utils"

/* global jest, describe, it, expect */

// Mock utility functions
jest.mock("../../modules/utils", () => {
  const actual = jest.requireActual("../../modules/utils")
  return {
    ...actual,
    indicatorForAttr: jest.fn(),
    replaceInString: jest.fn(),
  }
})

describe("TableRow Component", () => {
  it("renders correctly with given props", () => {
    const seqNum = "12345"
    const camera = {
      copy_row_template: "template-{dayObs}-{seqNum}",
      image_viewer_link:
        "http://lsst_{siteLoc}.lsst.org?image=MC_{controller:default=O}_{dayObs}_{seqNum}",
    }
    const channels = [
      { name: "channel1", colour: "#ff0000" },
      { name: "channel2", colour: "#00ff00" },
    ]
    const channelRow = {
      channel1: {
        key: "lsstcam/2025-05-29/event_timeline/000016/lsstcam_event_timeline_2025-05-29_000016.png",
        hash: "7d137112341f9b2b545e6fed37319cf0",
        camera_name: "lsstcam",
        day_obs: "2025-05-29",
        channel_name: "channel1",
        seq_num: 12345,
        filename: "lsstcam_event_timeline_2025-05-29_000016.png",
        ext: "png",
      },
      channel2: null,
    }
    const metadataColumns = [{ name: "controller" }, { name: "status" }]
    const metadataRow = {
      controller: "ctrl1",
      status: "active",
      "@channel2": "No Event",
    }

    // Mock utility function behavior
    indicatorForAttr.mockImplementation((_, attr) => `indicator-${attr}`)
    replaceInString.mockImplementation((template, dayObs, seqNum, options) =>
      template
        .replace("{dayObs}", dayObs)
        .replace("{seqNum}", seqNum)
        .replace("{siteLoc}", options.siteLoc || "default")
        .replace("{controller}", options.controller || "default")
    )

    const mockContextValue = {
      siteLocation: "summit",
      locationName: "test-location",
      camera: { name: "testcam", channels: [], title: "Test Cam" },
      dayObs: "2025-05-29",
    }

    render(
      <RubinTVTableContext.Provider value={mockContextValue}>
        <table>
          <tbody>
            <TableRow
              seqNum={seqNum}
              camera={camera}
              channels={channels}
              channelRow={channelRow}
              metadataColumns={metadataColumns}
              metadataRow={metadataRow}
            />
          </tbody>
        </table>
      </RubinTVTableContext.Provider>
    )

    // Assert sequence number cell
    expect(screen.getByText(seqNum)).toBeInTheDocument()

    // Assert channel cells
    expect(screen.getByRole("link", { name: /channel1/i })).toHaveAttribute(
      "href",
      expect.stringContaining("channel_name=channel1"),
      expect.stringContaining("day_obs=2025-05-29"),
      expect.stringContaining("seq_num=12345")
    )
    expect(screen.getByText("No Event")).toBeInTheDocument()

    // Assert metadata cells
    expect(screen.getByText("ctrl1")).toBeInTheDocument()
    expect(screen.getByText("active")).toBeInTheDocument()
  })
})
