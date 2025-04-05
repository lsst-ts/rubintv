import React, { useState, useEffect, StrictMode } from "react"
import { simplePost } from "../modules/utils"
import PropTypes from "prop-types"

export default function AdminPanel({ menus, isAdmin }) {
  return (
    <StrictMode>
      {isAdmin && (
        <div className="admin-indicator">
          <h3 className="admin-text">Hello Merlin</h3>
        </div>
      )}
      <div className="admin-panel">
        {menus.map((menu, index) => (
          <DropDownMenu key={index} menu={menu} />
        ))}
      </div>
    </StrictMode>
  )
}
AdminPanel.propTypes = {
  isAdmin: PropTypes.bool,
  menus: PropTypes.array,
}

export function DropDownMenu({ menu }) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)
  const [redisChanged, setRedisChanged] = useState(null)
  const toggleMenu = () => {
    setIsOpen(!isOpen)
  }

  useEffect(() => {
    setSelectedItem(menu.selectedItem)
  }, [menu.selectedItem])

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

    // Cleanup the event listener on component unmount or when `isOpen` changes
    return () => {
      window.removeEventListener("click", handleClickOutside)
    }
  }, [isOpen])

  const handleItemSelect = (item) => {
    const { value } = item
    simplePost("api/redis_post", { key: menu.key, value })
      .then((data) => {
        setRedisChanged(data)
      })
      .catch((error) => {
        setRedisChanged(false)
        console.error("Error posting to redis:", error)
      })
    setSelectedItem(item)
    setIsOpen(false)
  }
  const menuClass = isOpen ? "dropdown-menu" : "dropdown-menu hidden"
  const selectedTitle = selectedItem ? selectedItem.title : "- Select -"
  const selectedClass = selectedItem
    ? "dropdown-button"
    : "dropdown-button greyed-out"
  let successClass = ""
  if (redisChanged !== null) {
    successClass = redisChanged ? "success" : "fail"
    setTimeout(() => {
      setRedisChanged(null)
    }, 2000)
  }
  return (
    <div className="menu">
      <div className="menu-header">
        <h4 className="menu-title">{menu.title}</h4>
        <span className={successClass}></span>
      </div>
      <div className={menuClass}>
        <button className={selectedClass} onClick={toggleMenu}>
          {selectedTitle}
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
  menu: PropTypes.object,
}
