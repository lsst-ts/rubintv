import React, { useState, useEffect, createContext, useContext } from "react"
import { createPortal } from "react-dom"

interface ModalContextType {
  modalContent: React.ReactNode | null
  setModalContent: (content: React.ReactNode | null) => void
}

// Create a Context for the modal
const ModalContext = createContext<ModalContextType>({
  modalContent: null,
  setModalContent: () => {},
})

// Ensure modal-root exists in the DOM
const modalRoot =
  document.getElementById("modal-root") ||
  (() => {
    const root = document.createElement("div")
    root.id = "modal-root"
    document.body.appendChild(root)
    return root
  })()

export function ModalProvider({ children }: { children: React.ReactNode }) {
  const [modalContent, setModalContent] = useState<React.ReactNode | null>(null)

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModalContent(null)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  return (
    <ModalContext.Provider value={{ modalContent, setModalContent }}>
      {children}
      {modalContent &&
        createPortal(
          <div className="modal-overlay">
            <div className="modal-content">
              <button
                className="modal-close"
                onClick={() => setModalContent(null)}
              ></button>
              {modalContent}
            </div>
          </div>,
          modalRoot
        )}
    </ModalContext.Provider>
  )
}

export function useModal(): {
  modalContent: React.ReactNode | null
  showModal: (content: React.ReactNode) => void
  closeModal: () => void
} {
  const { modalContent, setModalContent } = useContext(ModalContext)

  const showModal = (content: React.ReactNode) => {
    setModalContent(content)
  }

  const closeModal = () => {
    setModalContent(null)
  }

  return { modalContent, showModal, closeModal }
}

export const ConfirmationModal = ({
  title = "Confirmation",
  message = "Are you sure?",
  onConfirm = () => {},
  onCancel = () => {},
}: {
  title?: string
  message?: string
  onConfirm?: () => void
  onCancel?: () => void
}) => {
  return (
    <div>
      <div className="modal-header">
        <h2>{title}</h2>
      </div>
      <p>{message}</p>
      <button onClick={onConfirm}>Yes</button>
      <button onClick={onCancel}>No</button>
    </div>
  )
}
