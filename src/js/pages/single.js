import React from "react"
import { createRoot } from "react-dom/client"
import { _getById } from "../modules/utils"
import PrevNext from "../components/PrevNext"

const { prevNext, eventURL } = window.APP_DATA

const prevNextRoot = createRoot(_getById("prev-next-nav"))
prevNextRoot.render(<PrevNext prevNext={prevNext} eventURL={eventURL} />)
