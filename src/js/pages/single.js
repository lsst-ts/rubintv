import React from 'react'
import { createRoot } from 'react-dom/client'
import { _getById } from "../modules/utils"
import PrevNext from "../components/PrevNext"

const prevNext = window.APP_DATA.prevNext

const prevNextRoot = createRoot(_getById('prev-next-nav'))
prevNextRoot.render(
  <PrevNext
    prevNext={prevNext}
  />
)
