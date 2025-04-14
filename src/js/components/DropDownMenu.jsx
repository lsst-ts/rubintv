import React, { useState, useEffect } from "react"
import PropTypes from "prop-types"

export default function DropDownMenu({ menu, onItemSelect }) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)

  useEffect(() => setSelectedItem(menu.selectedItem), [menu.selectedItem])

  const toggleMenu = () => setIsOpen(!isOpen)

  const handleItemSelect = (item) => {
    setSelectedItem(item)
    setIsOpen(false)
    if (onItemSelect) onItemSelect(item)
  }

  return (
    <div className="menu box">
      <div className="menu-header box-header">
        <h4 className="menu-title box-title">{menu.title}</h4>
      </div>
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
    </div>
  )
}

DropDownMenu.propTypes = {
  menu: PropTypes.object.isRequired,
  onItemSelect: PropTypes.func,
}
