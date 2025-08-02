import React, {
  useState,
  useEffect,
  createContext,
  useContext,
  useRef,
} from "react"
import { createPortal } from "react-dom"

interface ModalContextType {
  modalContent: React.ReactNode | null
  setModalContent: (content: React.ReactNode | null) => void
}

// Create a Context for the modal
/* istanbul ignore next */
const ModalContext = createContext<ModalContextType>({
  modalContent: null,
  setModalContent: () => {},
})

export function ModalProvider({ children }: { children: React.ReactNode }) {
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
