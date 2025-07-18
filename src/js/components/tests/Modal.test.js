import React from "react"
import { render, screen, fireEvent, act } from "@testing-library/react"
import "@testing-library/jest-dom"
import { ModalProvider, useModal, ConfirmationModal } from "../Modal"

/* global jest, describe, it, expect, beforeEach, afterEach */

// Test component that uses the modal hook
const TestComponent = () => {
  const { showModal, closeModal } = useModal()

  return (
    <div>
      <button
        onClick={() => showModal(<div>Test Modal Content</div>)}
        data-testid="open-modal"
      >
        Open Modal
      </button>
      <button onClick={closeModal} data-testid="close-modal">
        Close Modal
      </button>
    </div>
  )
}

describe("Modal", () => {
  let modalRoot

  beforeEach(() => {
    // Clean up any existing modal-root
    modalRoot = document.getElementById("modal-root")
    if (modalRoot) {
      document.body.removeChild(modalRoot)
    }
  })

  afterEach(() => {
    // Clean up modal-root after each test
    modalRoot = document.getElementById("modal-root")
    if (modalRoot) {
      document.body.removeChild(modalRoot)
    }
  })

  it("renders ModalProvider without crashing", () => {
    render(
      <ModalProvider>
        <div>Test Content</div>
      </ModalProvider>
    )
    expect(screen.getByText("Test Content")).toBeInTheDocument()
  })

  it("creates modal-root element when it doesn't exist", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)

    const modalRoot = document.getElementById("modal-root")
    expect(modalRoot).toBeInTheDocument()
  })

  it("does not create modal-root if it already exists", () => {
    // Create modal-root manually
    const existingRoot = document.createElement("div")
    existingRoot.id = "modal-root"
    document.body.appendChild(existingRoot)
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )
    const modalRoot = document.getElementById("modal-root")
    expect(modalRoot).toBe(existingRoot)
    expect(modalRoot.childNodes.length).toBe(0) // Ensure no children initially
  })

  it("opens modal when showModal is called", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)

    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()
    const modalOverlay = document.querySelector(".modal-overlay")
    const modalContent = document.querySelector(".modal-content")
    expect(modalOverlay).toBeInTheDocument()
    expect(modalContent).toBeInTheDocument()
  })

  it("closes modal when closeModal is called", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    // Open modal first
    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)
    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()

    // Close modal
    const closeButton = screen.getByTestId("close-modal")
    fireEvent.click(closeButton)
    expect(screen.queryByText("Test Modal Content")).not.toBeInTheDocument()
  })

  it("closes modal when close button is clicked", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    // Open modal
    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)
    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()

    // Click the X button
    const modalCloseButton = document.querySelector(".modal-close")
    fireEvent.click(modalCloseButton)

    expect(screen.queryByText("Test Modal Content")).not.toBeInTheDocument()
  })

  it("closes modal when Escape key is pressed", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    // Open modal
    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)
    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()

    // Press Escape key
    act(() => {
      fireEvent.keyDown(window, { key: "Escape", code: "Escape" })
    })

    expect(screen.queryByText("Test Modal Content")).not.toBeInTheDocument()
  })

  it("does not close modal when other keys are pressed", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    )

    // Open modal
    const openButton = screen.getByTestId("open-modal")
    fireEvent.click(openButton)
    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()

    // Press other keys
    act(() => {
      fireEvent.keyDown(window, { key: "Enter", code: "Enter" })
      fireEvent.keyDown(window, { key: "Space", code: "Space" })
    })

    expect(screen.getByText("Test Modal Content")).toBeInTheDocument()
  })
})

describe("ConfirmationModal", () => {
  it("renders with default props", () => {
    render(<ConfirmationModal />)

    expect(screen.getByText("Confirmation")).toBeInTheDocument()
    expect(screen.getByText("Are you sure?")).toBeInTheDocument()
    expect(screen.getByText("Yes")).toBeInTheDocument()
    expect(screen.getByText("No")).toBeInTheDocument()
  })

  it("renders with custom props", () => {
    render(
      <ConfirmationModal
        title="Delete Item"
        message="This action cannot be undone."
      />
    )

    expect(screen.getByText("Delete Item")).toBeInTheDocument()
    expect(
      screen.getByText("This action cannot be undone.")
    ).toBeInTheDocument()
  })

  it("calls onConfirm when Yes button is clicked", () => {
    const onConfirm = jest.fn()
    render(<ConfirmationModal onConfirm={onConfirm} />)

    const yesButton = screen.getByText("Yes")
    fireEvent.click(yesButton)

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it("calls onCancel when No button is clicked", () => {
    const onCancel = jest.fn()
    render(<ConfirmationModal onCancel={onCancel} />)

    const noButton = screen.getByText("No")
    fireEvent.click(noButton)

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it("works together with ModalProvider", () => {
    const TestConfirmationComponent = () => {
      const { showModal, closeModal } = useModal()

      const handleConfirm = () => {
        closeModal()
      }

      const handleCancel = () => {
        closeModal()
      }

      return (
        <div>
          <button
            onClick={() =>
              showModal(
                <ConfirmationModal
                  title="Delete File"
                  message="Are you sure you want to delete this file?"
                  onConfirm={handleConfirm}
                  onCancel={handleCancel}
                />
              )
            }
            data-testid="show-confirmation"
          >
            Show Confirmation
          </button>
        </div>
      )
    }

    render(
      <ModalProvider>
        <TestConfirmationComponent />
      </ModalProvider>
    )

    // Open confirmation modal
    const showButton = screen.getByTestId("show-confirmation")
    fireEvent.click(showButton)

    expect(screen.getByText("Delete File")).toBeInTheDocument()
    expect(
      screen.getByText("Are you sure you want to delete this file?")
    ).toBeInTheDocument()

    // Click Yes to close
    const yesButton = screen.getByText("Yes")
    fireEvent.click(yesButton)

    expect(screen.queryByText("Delete File")).not.toBeInTheDocument()
  })
})
