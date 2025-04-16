import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"

export default function DropDownMenu({ menu, onItemSelect }) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)

  useEffect(() => setSelectedItem(menu.selectedItem), [menu.selectedItem])
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest(".dropdown-menu")) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      window.addEventListener("click", handleClickOutside)
    } else {
      window.removeEventListener("click", handleClickOutside)
    }

    return () => {
      window.removeEventListener("click", handleClickOutside)
    }
  }
  , [isOpen])
  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      setIsOpen(false)
    }
  }
  useEffect(() => {
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown)
    } else {
      window.removeEventListener("keydown", handleKeyDown)
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }
  , [isOpen])

  const toggleMenu = () => setIsOpen(isOpen => !isOpen)

  const handleItemSelect = (item) => {
    setSelectedItem(item)
    setIsOpen(false)
    if (onItemSelect) onItemSelect(item)
  }

  return (
      <div className={isOpen ? "dropdown-menu" : "dropdown-menu hidden"}>
        <button
          className={
            selectedItem ? "dropdown-button" : "dropdown-button greyed-out"
          }
          onClick={toggleMenu}
        >
          {selectedItem ? selectedItem.title : "- Select -"}
        </button>
        <div className="dropdown-content">
          {menu.items.map((item, index) => (
            <li
              key={index}
              className="dropdown-item"
              onClick={() => handleItemSelect(item)}
            >
              {item.title}
            </li>
          ))}
        </div>
      </div>
  )
}

DropDownMenu.propTypes = {
  menu: PropTypes.object.isRequired,
  onItemSelect: PropTypes.func,
}
