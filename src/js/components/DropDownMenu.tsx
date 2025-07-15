import React, { useState, useEffect } from "react"

export interface Menu {
  key: string
  title: string
  items: Array<MenuItem>
  selectedItem?: MenuItem | null
}

export interface MenuItem {
  title: string
  value?: string
}

interface DropDownMenuProps {
  menu: Menu
  onItemSelect?: (item: MenuItem) => void
}

export default function DropDownMenu({
  menu,
  onItemSelect,
}: DropDownMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)

  useEffect(() => setSelectedItem(menu.selectedItem), [menu.selectedItem])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest(".dropdown-menu")) {
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
  }, [isOpen])
  const handleKeyDown = (event: KeyboardEvent) => {
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
  }, [isOpen])

  const toggleMenu = () => setIsOpen((isOpen) => !isOpen)

  const handleItemSelect = (item: MenuItem) => {
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
