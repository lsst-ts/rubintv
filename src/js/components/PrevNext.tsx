import React, { useEffect, useRef, useState, useContext } from "react"
import { PrevNextType } from "./componentTypes"
import { RubinTVTableContext, RubinTVContextType } from "./componentTypes"
import { setCameraBaseUrl } from "../modules/utils"

export default function PrevNext({
  initialPrevNext,
}: {
  initialPrevNext: PrevNextType
}) {
  const [prevNext, setPrevNext] = useState(initialPrevNext)
  if (!prevNext) {
    return null
  }
  const { locationName, camera } = useContext(
    RubinTVTableContext
  ) as RubinTVContextType
  const { getEventUrl } = setCameraBaseUrl(locationName, camera.name)
  const left = useRef<HTMLAnchorElement>(null)
  const right = useRef<HTMLAnchorElement>(null)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key == "Right") {
        right.current?.click()
      }
      if (e.key == "Left") {
        left.current?.click()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return function cleanup() {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  useEffect(() => {
    type EL = EventListener
    function handleNewPrevNext(e: CustomEvent) {
      const { data, dataType } = e.detail
      if (dataType == "prevNext") {
        const { prev, next } = data
        setPrevNext({ prev, next })
      }
    }

    window.addEventListener("channel", handleNewPrevNext as EL)
    return () => {
      window.removeEventListener("channel", handleNewPrevNext as EL)
    }
  }, [])

  const prev = prevNext.prev
  const next = prevNext.next

  return (
    <div className="prev-next-buttons">
      {prev && (
        <a
          className="prev prev-next button"
          href={getEventUrl(prev)}
          ref={left}
        >
          {prev.seq_num}
        </a>
      )}
      {next && (
        <a
          className="next prev-next button"
          href={getEventUrl(next)}
          ref={right}
        >
          {next.seq_num}
        </a>
      )}
    </div>
  )
}
