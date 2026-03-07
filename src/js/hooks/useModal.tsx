import React, { useContext } from "react"
import { ModalContext } from "../components/contexts/contexts"

export function useModal(): {
  modalHeader?: string | null
  modalContent: React.ReactNode | null
  showModal: (content: React.ReactNode, header: string | null) => void
  closeModal: () => void
} {
  const { modalHeader, modalContent, setModalContent, setModalHeader } =
    useContext(ModalContext)

  const showModal = (content: React.ReactNode, header: string | null) => {
    setModalContent(content)
    setModalHeader(header)
  }

  const closeModal = () => {
    setModalContent(null)
    setModalHeader(null)
  }

  return { modalHeader, modalContent, showModal, closeModal }
}
