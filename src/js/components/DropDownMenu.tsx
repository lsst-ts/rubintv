import React, { useState, useEffect } from "react"

export interface Menu {
  key: string
  title: string
  items: Array<string>
  selectedItem?: string
}

interface DropDownMenuProps {
  menu: Menu
  onItemSelect?: (item: string) => void
}

export default function DropDownMenu({
  menu,
  onItemSelect,
}: DropDownMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest(".dropdown-menu")) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener("click", handleClickOutside)
    } else {
      document.removeEventListener("click", handleClickOutside)
    }

    return () => {
      document.removeEventListener("click", handleClickOutside)
    }
  }, [isOpen])
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      setIsOpen(false)
    }
  }
  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown)
    } else {
      document.removeEventListener("keydown", handleKeyDown)
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen])

  const toggleMenu = () => setIsOpen((isOpen) => !isOpen)

  const handleItemSelect = (item: string) => {
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
        {selectedItem || selectedItem === "" ? selectedItem : "- Select -"}
      </button>
      <div className="dropdown-content">
        {menu.items.map((item, index) => (
          <li
            key={index}
            className="dropdown-item"
            onClick={() => handleItemSelect(item)}
          >
            {item}
          </li>
        ))}
      </div>
    </div>
  )
}
