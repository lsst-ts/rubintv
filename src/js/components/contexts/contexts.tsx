import { createContext, useContext } from "react"
import {
  RubinTVContextType,
  RedisEndpoint,
  ModalContextType,
} from "../componentTypes"

export const RubinTVTableContext = createContext<
  RubinTVContextType | undefined
>(undefined)

export const RedisEndpointContext = createContext<RedisEndpoint | null>(null)

export const useRedisEndpoint = () => {
  const context = useContext(RedisEndpointContext)
  if (context === null) {
    throw new Error(
      "useRedisEndpoint must be used within a RedisEndpointProvider"
    )
  }
  return context
}

// Create a Context for the modal
/* istanbul ignore next */
export const ModalContext = createContext<ModalContextType>({
  modalContent: null,
  setModalContent: () => {},
})
