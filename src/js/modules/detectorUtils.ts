// Helper functions for Detector components

export const RESET_PREFIX = "RUBINTV_CONTROL_RESET_"

export const getStatusClass = (status: string) => {
  switch (status) {
    case "free":
      return "status-free"
    case "busy":
      return "status-busy"
    case "queued":
      return "status-queued"
    case "restarting":
      return "status-restarting"
    case "guest":
      return "status-guest"
    default:
      return "status-missing"
  }
}

export const getStatusColor = (status: string) => {
  switch (status) {
    case "free":
      return "#22c55e"
    case "busy":
      return "#eab308"
    case "queued":
      return "#ef4444"
    case "restarting":
      return "#a163ac"
    case "guest":
      return "#3b82f6"
    default:
      return "#d1d5db"
  }
}

export const createPlaceholders = (count: number) => {
  const placeholders: Record<string, Record<string, string>> = {}
  for (let i = 0; i < count; i++) {
    placeholders[i.toString()] = { status: "missing" }
  }
  return placeholders
}
