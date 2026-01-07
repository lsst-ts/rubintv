import React, { useState, useEffect } from "react"
import { createPortal } from "react-dom"
import { ModalContext } from "./contexts/contexts"
import { ConfirmationModalProps } from "./componentTypes"

export const ModalProvider = ({ children }: { children: React.ReactNode }) => {
  const [modalContent, setModalContent] = useState<React.ReactNode | null>(null)

  // Create or get modal-root element lazily
  const getModalRoot = () => {
    return (
      document.getElementById("modal-root") ||
      (() => {
        const root = document.createElement("div")
        root.id = "modal-root"
        document.body.appendChild(root)
        return root
      })()
    )
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModalContent(null)
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
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
          getModalRoot()
        )}
    </ModalContext.Provider>
  )
}

export const ConfirmationModal = ({
  title = "Confirmation",
  message = "Are you sure?",
  onConfirm = () => {},
  onCancel = () => {},
}: ConfirmationModalProps) => {
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
