import React from "react"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { FilterDialog } from "../TableFilter"
import { useModal } from "../Modal"

/* global jest, describe, it, expect, beforeEach */

jest.mock("../Modal", () => ({
  useModal: jest.fn(),
}))

const mockUseModal = useModal

describe("FilterDialog", () => {
  const mockSetFilterOn = jest.fn()
  const mockCloseModal = jest.fn()

  const defaultProps = {
    column: "name",
    setFilterOn: mockSetFilterOn,
    filterOn: { column: "", value: "" },
    filteredRowsCount: 10,
    unfilteredRowsCount: 20,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseModal.mockReturnValue({
      closeModal: mockCloseModal,
    })
  })

  const renderFilterDialog = (props = {}) => {
    return render(<FilterDialog {...defaultProps} {...props} />)
  }

  describe("Rendering", () => {
    it("renders the filter dialog with correct heading", () => {
      renderFilterDialog()
      expect(
        screen.getByRole("heading", { name: "filter on name" })
      ).toBeInTheDocument()
    })

    it("renders input with correct placeholder", () => {
      renderFilterDialog()
      expect(screen.getByPlaceholderText("Enter name...")).toBeInTheDocument()
    })

    it("renders Apply and Clear buttons", () => {
      renderFilterDialog()
      expect(screen.getByRole("button", { name: "Apply" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument()
    })

    it("does not show filter info when no filter is applied", () => {
      renderFilterDialog()
      expect(
        screen.queryByText(/Currently filtering by:/)
      ).not.toBeInTheDocument()
    })

    it("shows filter info when filter is applied", () => {
      renderFilterDialog({
        filterOn: { column: "name", value: "test" },
      })
      expect(
        screen.getByText("Currently filtering by: test")
      ).toBeInTheDocument()
      expect(screen.getByText("10 of 20 total rows")).toBeInTheDocument()
    })

    it("renders with different column name", () => {
      renderFilterDialog({ column: "email" })
      expect(
        screen.getByRole("heading", { name: "filter on email" })
      ).toBeInTheDocument()
      expect(screen.getByPlaceholderText("Enter email...")).toBeInTheDocument()
    })
  })

  describe("Focus behavior", () => {
    it("focuses the input on mount", async () => {
      renderFilterDialog()
      const input = screen.getByPlaceholderText("Enter name...")
      await waitFor(() => {
        expect(input).toHaveFocus()
      })
    })
  })

  describe("User interactions", () => {
    it("calls setFilterOn and closeModal when Apply button is clicked", async () => {
      renderFilterDialog()

      const input = screen.getByPlaceholderText("Enter name...")
      fireEvent.input(input, { target: { value: "test value" } })
      fireEvent.click(screen.getByRole("button", { name: "Apply" }))

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "name",
        value: "test value",
      })
      expect(mockCloseModal).toHaveBeenCalled()
    })

    it("trims whitespace from input value when applying filter", async () => {
      renderFilterDialog()

      const input = screen.getByPlaceholderText("Enter name...")
      fireEvent.input(input, { target: { value: "  test value  " } })
      fireEvent.click(screen.getByRole("button", { name: "Apply" }))

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "name",
        value: "test value",
      })
    })

    it("calls setFilterOn with empty values and closeModal when Clear button is clicked", async () => {
      renderFilterDialog()

      fireEvent.click(screen.getByRole("button", { name: "Clear" }))

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "",
        value: "",
      })
      expect(mockCloseModal).toHaveBeenCalled()
    })

    it("applies filter when Enter key is pressed", async () => {
      renderFilterDialog()

      const input = screen.getByPlaceholderText("Enter name...")
      fireEvent.input(input, { target: { value: "test value" } })
      fireEvent.keyDown(input, { key: "Enter", code: "Enter", charCode: 13 })

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "name",
        value: "test value",
      })
      expect(mockCloseModal).toHaveBeenCalled()
    })

    it("does not apply filter when other keys are pressed", async () => {
      renderFilterDialog()

      const input = screen.getByPlaceholderText("Enter name...")
      fireEvent.input(input, { target: { value: "test" } })
      fireEvent.keyDown(input, { key: "Escape", code: "Escape", charCode: 27 })

      expect(mockSetFilterOn).not.toHaveBeenCalled()
      expect(mockCloseModal).not.toHaveBeenCalled()
    })
  })

  describe("Edge cases", () => {
    it("handles empty input value when applying filter", async () => {
      renderFilterDialog()

      fireEvent.click(screen.getByRole("button", { name: "Apply" }))

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "name",
        value: "",
      })
      expect(mockCloseModal).toHaveBeenCalled()
    })

    it("handles whitespace-only input value when applying filter", async () => {
      renderFilterDialog()

      const input = screen.getByPlaceholderText("Enter name...")
      fireEvent.input(input, { target: { value: "   " } })
      fireEvent.click(screen.getByRole("button", { name: "Apply" }))

      expect(mockSetFilterOn).toHaveBeenCalledWith({
        column: "name",
        value: "",
      })
    })

    it("shows correct row counts with different numbers", () => {
      renderFilterDialog({
        filterOn: { column: "name", value: "test" },
        filteredRowsCount: 5,
        unfilteredRowsCount: 100,
      })
      expect(screen.getByText("5 of 100 total rows")).toBeInTheDocument()
    })

    it("handles zero filtered rows", () => {
      renderFilterDialog({
        filterOn: { column: "name", value: "test" },
        filteredRowsCount: 0,
        unfilteredRowsCount: 50,
      })
      expect(screen.getByText("0 of 50 total rows")).toBeInTheDocument()
    })
  })
})
