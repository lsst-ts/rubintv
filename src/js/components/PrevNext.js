import React, { useEffect, useRef } from "react"
import PropTypes from "prop-types"
import { eventType } from "./componentPropTypes"

export default function PrevNext({ prevNext, eventUrl }) {
  const left = useRef(null)
  const right = useRef(null)
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.keyCode == 39) {
        right.current?.click()
      }
      if (e.keyCode == 37) {
        left.current?.click()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return function cleanup() {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [])
  const prev = prevNext.prev
  const next = prevNext.next
  return (
    <div className="prev-next-buttons">
      {prev && (
        <a
          className="prev prev-next button"
          href={`${eventUrl}?key=${prev.key}`}
          ref={left}
        >
          {prev.seq_num}
        </a>
      )}
      {next && (
        <a
          className="next prev-next button"
          href={`${eventUrl}?key=${next.key}`}
          ref={right}
        >
          {next.seq_num}
        </a>
      )}
    </div>
  )
}
PrevNext.propTypes = {
  prevNext: PropTypes.oneOfType([
    PropTypes.shape({
      next: eventType,
      prev: PropTypes.oneOfType([eventType, PropTypes.string]),
    }),
    PropTypes.object,
  ]),
  eventUrl: PropTypes.string,
}
