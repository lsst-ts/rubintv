import React from "react";
import PropTypes from 'prop-types'
import { eventType } from "./componentPropTypes"

export default function PrevNext ({prevNext}) {
  const eventURL = window.APP_DATA.eventURL
  const prev = prevNext.prev
  const next = prevNext.next
  return (
    <div className="prev-next-buttons">
      { prev && (
        <a
          className="prev prev-next button"
          href={`${eventURL}?key=${prev.key}`}
        >
          { prev.seq_num }
        </a>
      )}
      { next && (
        <a
          className="next prev-next button"
          href={`${eventURL}?key=${next.key}`}
          >
          { next.seq_num }
        </a>
      )}
    </div>
  )
}
PrevNext.propTypes = {
  prevNext: PropTypes.oneOfType(
    [
      PropTypes.shape({
        next: eventType,
        prev: PropTypes.oneOfType([eventType, PropTypes.string])
      }),
      PropTypes.object
    ]
  )
}
