import React from "react"
import PropTypes from "prop-types"

export default function TableFilter() {
  return (
    <div>
      <h2>Table Filter</h2>
    </div>
  )
}

export function ColumnFilterInput({ column }) {
  console.log("In ColumnFilter with column: ", column)
  const placeholder = `Filter using ${column}...`
  return <input type="text" placeholder={placeholder} />
}
ColumnFilterInput.propTypes = {
  column: PropTypes.string,
}
