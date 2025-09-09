import { createContext } from "react"
import { RubinTVContextType, RedisEndpoint } from "../componentTypes"

export const RubinTVTableContext = createContext<
  RubinTVContextType | undefined
>(undefined)

export const RedisEndpointContext = createContext<RedisEndpoint | null>(null)
