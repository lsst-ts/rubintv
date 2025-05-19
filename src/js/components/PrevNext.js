import React, { useEffect, useRef } from "react"
import PropTypes from "prop-types"
import { eventType } from "./componentPropTypes"

export default function PrevNext({ prevNext, eventUrl }) {
  if (!prevNext) {
    return null
  }
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
  const makeUrl = (obj) => {
    const { channel_name, day_obs, seq_num } = obj
    return `${eventUrl}?channel_name=${channel_name}&date_str=${day_obs}&seq_num=${seq_num}`
  }
  return (
    <div className="prev-next-buttons">
      {prev && (
        <a className="prev prev-next button" href={makeUrl(prev)} ref={left}>
          {prev.seq_num}
        </a>
      )}
      {next && (
        <a className="next prev-next button" href={makeUrl(next)} ref={right}>
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
