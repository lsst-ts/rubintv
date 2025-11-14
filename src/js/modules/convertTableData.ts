import { ChannelData } from "../components/componentTypes"

/**
 * Converts structured data and extension information into a table format
 * similar to what make_table_from_event_list produces in the Python backend.
 *
 * @param locationName - The name of the location
 * @param cameraName - The name of the camera
 * @param dateStr - ISO format date string (YYYY-MM-DD)
 * @param data - Structured data from historical.get_structured_data_for_date
 * @param extensionInfo - Extension information from historical.get_all_extensions_for_date
 * @param channels - List of channel objects to include in the table
 * @returns A dictionary with sequence numbers as keys and channel data as values
 */
export function createTableFromStructuredData(
  cameraName: string,
  dateStr: string,
  data: Record<
    string,
    Set<number | string> | Array<number | string> | Record<string, any>
  >,
  extensionInfo: Record<
    string,
    { default: string; exceptions: Record<string | number, string> }
  >,
  channels: Array<{ name: string }>
): ChannelData {
  // Initialize the result table
  const tableData: ChannelData = {}

  // Find all unique sequence numbers across all channels
  const allSeqNums = new Set<number>()

  // Helper function to check if a seq_num exists in the data structure
  // This handles both Set objects and arrays/objects from JSON
  const hasSeqNum = (channelData: any, seqNum: number | string): boolean => {
    if (channelData instanceof Set) {
      return channelData.has(seqNum)
    } else if (Array.isArray(channelData)) {
      return channelData.includes(seqNum)
    } else if (typeof channelData === "object") {
      // If it's an object with sequence numbers as keys or values
      return (
        Object.keys(channelData).includes(String(seqNum)) ||
        Object.values(channelData).includes(seqNum)
      )
    }
    return false
  }

  // Convert data to collect all unique sequence numbers
  Object.entries(data).forEach(([, channelData]) => {
    // Handle different formats (Set, Array, Object)
    if (channelData instanceof Set) {
      channelData.forEach((seqNum) => {
        if (typeof seqNum === "number") {
          allSeqNums.add(seqNum)
        }
      })
    } else if (Array.isArray(channelData)) {
      channelData.forEach((seqNum) => {
        if (typeof seqNum === "number") {
          allSeqNums.add(seqNum)
        }
      })
    } else if (typeof channelData === "object") {
      // Handle object format (e.g., from JSON)
      Object.keys(channelData).forEach((key) => {
        const seqNum = Number(key)
        if (!isNaN(seqNum)) {
          allSeqNums.add(seqNum)
        }
      })
    }
  })

  // Sort sequence numbers
  const sortedSeqNums = Array.from(allSeqNums).sort((a, b) => a - b)

  // Build the table structure
  sortedSeqNums.forEach((seqNum) => {
    tableData[seqNum] = {}

    // Process each channel
    channels.forEach((channel) => {
      const channelName = channel.name

      // Skip channels not in our data or that don't have this sequence number
      if (!data[channelName] || !hasSeqNum(data[channelName], seqNum)) {
        return
      }

      // Get the extension for this sequence number
      let extension = extensionInfo[channelName]?.default || "jpg"
      if (extensionInfo[channelName]?.exceptions[seqNum]) {
        extension = extensionInfo[channelName].exceptions[seqNum]
      }

      // Reconstruct the filename
      const filename = `${cameraName}_${channelName}_${String(seqNum).padStart(6, "0")}.${extension}`

      // Reconstruct the key
      const key = `${cameraName}/${dateStr}/${channelName}/${String(seqNum).padStart(6, "0")}/${filename}`

      // Create event-like object for this channel at this sequence number
      tableData[seqNum][channelName] = {
        key,
        camera_name: cameraName,
        day_obs: dateStr,
        channel_name: channelName,
        seq_num: `${seqNum}`,
        filename,
        ext: extension,
      }
    })
  })

  return tableData
}
