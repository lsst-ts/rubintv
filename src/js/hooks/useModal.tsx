import React, { useContext } from "react"
import { ModalContext } from "../components/contexts/contexts"

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
