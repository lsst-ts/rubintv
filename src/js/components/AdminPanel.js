import React, { useState } from "react"

export default function DropDownMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const menuItems = [
    { title: "Apple", value: "apple" },
    { title: "Banana", value: "banana" },
    { title: "Cherry", value: "cherry" },
  ]
  const toggleMenu = () => {
    setIsOpen(!isOpen)
  }
  const contentClass = isOpen ? "dropdown-content" : "dropdown-content hidden"
  return (
    <div className="dropdown">
      <button onClick={toggleMenu}>Test Item</button>
      <div className={contentClass}>
        {menuItems.map((item, index) => (
          <li key={index} className="dropdown-item">
            <a href="#">{item.title}</a>
          </li>
        ))}
      </div>
    </div>
  )
}
