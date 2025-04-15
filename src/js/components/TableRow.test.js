/* eslint-env jest */
import "@testing-library/jest-dom" // Import jest-dom for custom matchers
import React from "react"
import { render, screen } from "@testing-library/react"
import { TableRow } from "./TableView" // Import TableRow directly
import { indicatorForAttr, replaceInString } from "../modules/utils"

/* global jest, describe, it, expect, beforeAll */

// Mock utility functions
jest.mock("../modules/utils", () => ({
  indicatorForAttr: jest.fn(),
  replaceInString: jest.fn(),
}))

// Add a mock `modal-root` to the DOM
beforeAll(() => {
  const modalRoot = document.createElement("div")
  modalRoot.setAttribute("id", "modal-root")
  document.body.appendChild(modalRoot)
})

describe("TableRow Component", () => {
  it("renders correctly with given props", () => {
    const seqNum = "12345"
    const camera = {
      copy_row_template: "template-{dayObs}-{seqNum}",
      image_viewer_link: "http://example.com/{siteLoc}/{seqNum}",
    }
    const channels = [
      { name: "channel1", colour: "#ff0000" },
      { name: "channel2", colour: "#00ff00" },
    ]
    const channelRow = {
      channel1: { key: "event1" },
      channel2: null,
    }
    const metadataColumns = [{ name: "controller" }, { name: "status" }]
    const metadataRow = {
      controller: "ctrl1",
      status: "active",
      "@channel2": "No Event",
    }

    // Mock utility function behavior
    indicatorForAttr.mockImplementation(
      (attributes, attr) => `indicator-${attr}`
    )
    replaceInString.mockImplementation((template, dayObs, seqNum, options) =>
      template.replace("{dayObs}", dayObs).replace("{seqNum}", seqNum)
    )

    render(
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
    )

    // Assert sequence number cell
    expect(screen.getByText(seqNum)).toBeInTheDocument()

    // Assert channel cells
    expect(screen.getByRole("link", { name: /channel1/i })).toHaveAttribute(
      "href",
      expect.stringContaining("event1")
    )
    expect(screen.getByText("No Event")).toBeInTheDocument()

    // Assert metadata cells
    expect(screen.getByText("ctrl1")).toBeInTheDocument()
    expect(screen.getByText("active")).toBeInTheDocument()
  })
})
