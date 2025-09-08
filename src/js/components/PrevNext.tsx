import React, { useEffect, useRef, useState, useContext } from "react"
import { PrevNextType } from "./componentTypes"
import { RubinTVContextType } from "./componentTypes"
import { RubinTVTableContext } from "./contexts/contexts"
import { setCameraBaseUrl } from "../modules/utils"

type EL = EventListener

export default function PrevNext({
  initialPrevNext,
}: {
  initialPrevNext: PrevNextType
}) {
  const [prevNext, setPrevNext] = useState(initialPrevNext)
  const { locationName, camera } = useContext(
    RubinTVTableContext
  ) as RubinTVContextType
  const { getEventUrl } = setCameraBaseUrl(locationName, camera.name)
  const left = useRef<HTMLAnchorElement>(null)
  const right = useRef<HTMLAnchorElement>(null)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key == "ArrowRight") {
        right.current?.click()
      }
      if (e.key == "ArrowLeft") {
        left.current?.click()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return function cleanup() {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  useEffect(() => {
    function handleNewPrevNext(e: CustomEvent) {
      const { data, dataType } = e.detail
      if (dataType == "prevNext") {
        if (!data) {
          return
        }
        const { prev, next } = data
        if (!prev && !next) {
          return
        }
        setPrevNext({ prev, next })
      }
    }

    window.addEventListener("channel", handleNewPrevNext as EL)
    return () => {
      window.removeEventListener("channel", handleNewPrevNext as EL)
    }
  }, [])

  if (!prevNext) {
    return null
  }
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
