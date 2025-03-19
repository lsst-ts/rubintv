import React, { createContext, useContext, useState } from "react"
import PropTypes from "prop-types"

// Create a Context for the modal
const ModalContext = createContext()

export const ModalProvider = ({ children }) => {
  const [modalContent, setModalContent] = useState(null)

  const showModal = (content) => setModalContent(content)
  const closeModal = () => setModalContent(null)

  return (
    <ModalContext.Provider value={{ showModal, closeModal }}>
      {children}
      {modalContent && <Modal>{modalContent}</Modal>}
    </ModalContext.Provider>
  )
}
ModalProvider.propTypes = {
  children: PropTypes.node,
}

export const useModal = () => useContext(ModalContext)

const Modal = ({ children }) => {
  const { closeModal } = useModal()

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      closeModal()
    }
  }
  return (
    <div
      className="modal-overlay"
      onKeyDown={handleKeyDown}
      onClick={closeModal}
      tabIndex="0"
    >
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {children}
        <button onClick={closeModal}>Cancel</button>
      </div>
    </div>
  )
}
Modal.propTypes = {
  children: PropTypes.node,
}
