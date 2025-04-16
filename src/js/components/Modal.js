import React, { useState, useEffect, createContext, useContext } from "react"
import { createPortal } from "react-dom"
import PropTypes from "prop-types"

// Create a Context for the modal
const ModalContext = createContext()

// Ensure modal-root exists in the DOM
const modalRoot =
  document.getElementById("modal-root") ||
  (() => {
    const root = document.createElement("div")
    root.id = "modal-root"
    document.body.appendChild(root)
    return root
  })()

export function ModalProvider({ children }) {
  const [modalContent, setModalContent] = useState(null)

  useEffect(() => {
    const handleKeyDown = (event) => {
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
ModalProvider.propTypes = {
  children: PropTypes.node,
}

export function useModal() {
  const { modalContent, setModalContent } = useContext(ModalContext)

  const showModal = (content) => {
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
ConfirmationModal.propTypes = {
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
}
