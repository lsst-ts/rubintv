import React, { useState, useEffect } from "react"
import { createPortal } from "react-dom"
import { ModalContext } from "./contexts/contexts"
import { ConfirmationModalProps } from "./componentTypes"

export const ModalProvider = ({ children }: { children: React.ReactNode }) => {
  const [modalContent, setModalContent] = useState<React.ReactNode | null>(null)
  const [modalHeader, setModalHeader] = useState<string | null>(null)

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
        setModalHeader(null)
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const modalContentElement = document.querySelector(
        ".modal-wrapper"
      ) as HTMLElement
      if (
        modalContentElement &&
        !modalContentElement.contains(event.target as Node)
      ) {
        setModalContent(null)
        setModalHeader(null)
      }
    }

    if (modalContent) {
      document.addEventListener("mousedown", handleClickOutside)
    } else {
      document.removeEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [modalContent])

  return (
    <ModalContext.Provider
      value={{ modalHeader, setModalHeader, modalContent, setModalContent }}
    >
      {children}
      {modalContent &&
        createPortal(
          <div className="modal-overlay">
            <div className="modal-wrapper">
              <div className="modal-header">
                {modalHeader && <h2>{modalHeader}</h2>}
                <button
                  className="modal-close"
                  onClick={() => {
                    setModalContent(null)
                    setModalHeader(null)
                  }}
                ></button>
              </div>
              <div className="modal-content">{modalContent}</div>
            </div>
          </div>,
          getModalRoot()
        )}
    </ModalContext.Provider>
  )
}

export const ConfirmationModal = ({
  message = "Are you sure?",
  onConfirm = () => {},
  onCancel = () => {},
}: ConfirmationModalProps) => {
  return (
    <div className="confirmation-modal">
      <p>{message}</p>
      <div className="confirmation-buttons">
        <button onClick={onConfirm}>Yes</button>
        <button onClick={onCancel}>No</button>
      </div>
    </div>
  )
}
