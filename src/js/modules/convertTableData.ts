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
  data: Record<string, Set<number | string>>,
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

  // Convert string seq numbers to integers and collect all unique ones
  Object.entries(data).forEach(([, seqNums]) => {
    seqNums.forEach((seqNum) => {
      // Skip 'final' or other non-numeric seq numbers for the main table
      if (typeof seqNum === "number") {
        allSeqNums.add(seqNum)
      }
    })
  })

  // Sort sequence numbers
  const sortedSeqNums = Array.from(allSeqNums).sort((a, b) => a - b)

  // Build the table structure
  sortedSeqNums.forEach((seqNum) => {
    tableData[seqNum] = {}

    // Process each channel
    channels.forEach((channel) => {
      const channelName = channel.name

      // Skip channels not in our data
      if (!data[channelName]?.has(seqNum)) {
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
