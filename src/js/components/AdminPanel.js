import React, { useState } from "react"
import { simplePost } from "../modules/utils"

export default function DropDownMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const menuItems = [
    { title: "Send apple", value: "apple" },
    { title: "Send 123", value: "123" },
  ]
  const toggleMenu = () => {
    setIsOpen(!isOpen)
    if (!isOpen) {
      const handleClickOutside = (event) => {
        if (!event.target.closest(".dropdown")) {
          setIsOpen(false)
          window.removeEventListener("click", handleClickOutside)
        }
      }
      window.addEventListener("click", handleClickOutside)
    }
  }
  const handleItemClick = (value) => {
    simplePost("api/test_send", { value }).then((data) => {
      console.log(data)
    })
    setIsOpen(false)
  }
  const contentClass = isOpen ? "dropdown-content" : "dropdown-content hidden"
  return (
    <div className="dropdown">
      <button onClick={toggleMenu}>Test Item</button>
      <div className={contentClass}>
        {menuItems.map((item, index) => (
          <li
            key={index}
            className="dropdown-item"
            onClick={() => handleItemClick(item.value)}
          >
            <a href="#">{item.title}</a>
          </li>
        ))}
      </div>
    </div>
  )
}
