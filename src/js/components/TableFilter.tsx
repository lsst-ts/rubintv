import React, { KeyboardEvent, useEffect, useRef } from "react"
import { useModal } from "../hooks/useModal"
import { TableFilterDialogProps } from "./componentTypes"

export function FilterDialog({
  column,
  setFilterOn,
  filterOn,
  filteredRowsCount,
  unfilteredRowsCount,
}: TableFilterDialogProps) {
  const placeholder = `Enter ${column}...`
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (!inputRef.current) return
    inputRef.current.focus()
  }, [])

  const { closeModal } = useModal()

  const handleApply = () => {
    if (!inputRef.current) return
    const value = inputRef.current.value.trim()
    setFilterOn({ column, value })
    closeModal()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
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
