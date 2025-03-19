import React, { useEffect, useRef } from "react"
import PropTypes from "prop-types"
import { useModal } from "./Modal"

export default function TableFilter() {
  return (
    <div>
      <h2>Table Filter</h2>
    </div>
  )
}

export function FilterDialog({ column, setFilterOn }) {
  const placeholder = `Enter ${column}...`
  const inputRef = useRef(null)
  useEffect(() => {
    inputRef.current.focus()
  }, [])

  const { closeModal } = useModal()

  const handleApply = () => {
    const value = inputRef.current.value
    setFilterOn({ column, value: value })
    closeModal()
  }

  const handleKeyDown = (e) => {
    console.log(e.key)
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
      <h2>Filter by {column}</h2>
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
}
