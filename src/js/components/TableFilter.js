import React, { useEffect, useRef } from "react"
import PropTypes from "prop-types"
import { useModal } from "./Modal"

export function FilterDialog({
  column,
  setFilterOn,
  filterOn,
  filteredRowsCount,
  unfilteredRowsCount,
}) {
  const placeholder = `Enter ${column}...`
  const inputRef = useRef(null)
  useEffect(() => {
    inputRef.current.focus()
  }, [])

  const { closeModal } = useModal()

  const handleApply = () => {
    const value = inputRef.current.value.trim()
    setFilterOn({ column, value })
    closeModal()
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleApply()
    }
  }

  const handleClear = () => {
    setFilterOn({ column: "", value: "" })
    closeModal()
  }

  return (
    <>
      <h2>filter on {column}</h2>
      {!!filterOn.value && (
        <div className="filter-info">
          <p>Currently filtering by: {filterOn.value}</p>
          <p>
            {filteredRowsCount} of {unfilteredRowsCount} total rows
          </p>
        </div>
      )}
      <input
        ref={inputRef}
        name="value"
        type="text"
        placeholder={placeholder}
        onKeyDown={handleKeyDown}
      />
      <button onClick={handleApply}>Apply</button>
      <button onClick={handleClear}>Clear</button>
    </>
  )
}
FilterDialog.propTypes = {
  column: PropTypes.string,
  setFilterOn: PropTypes.func,
  filterOn: PropTypes.object,
  filteredRowsCount: PropTypes.number,
  unfilteredRowsCount: PropTypes.number,
}
