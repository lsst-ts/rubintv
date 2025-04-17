import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
// import PrevNext from "../components/PrevNext"
import MediaDisplay from "../components/MediaDisplay"

// const { prevNext, eventUrl } = window.APP_DATA

// const prevNextRoot = createRoot(_getById("prev-next-nav"))
// prevNextRoot.render(<PrevNext prevNext={prevNext} eventUrl={eventUrl} />)
const mediaDisplayRoot = createRoot(_getById("event-display"))
mediaDisplayRoot.render(
  <MediaDisplay
    initialData={initEvent.data}
    imgUrl={imgUrl}
    movieUrl={movieUrl}
    baseUrl={baseUrl}
  />
)
