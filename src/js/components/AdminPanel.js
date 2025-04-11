import React, { useState, useEffect, StrictMode } from "react"
import { simplePost, simpleGet } from "../modules/utils"
import PropTypes from "prop-types"

export default function AdminPanel({
  initMenus,
  initAdmin,
  redisGetURL,
  authAPIURL,
}) {
  const [admin, setAdmin] = useState(initAdmin)
  const [menus, setMenus] = useState(initMenus)

  useEffect(() => {
    // Fetch the admin user info
    simpleGet(authAPIURL).then((dataStr) => {
      try {
        // check that the response is valid JSON
        JSON.parse(dataStr)
      } catch (e) {
        console.error("Error parsing auth api JSON response:", e)
        return
      }
      const data = JSON.parse(dataStr)
      // check that the username is the same as the admin username
      if (data.username !== admin.username) {
        console.error(
          `User ${data.username} is not the admin user ${admin.username}.`
        )
      }
      setAdmin((prevAdmin) => ({
        ...prevAdmin,
        email: data.email,
        name: data.name,
      }))
    })
  }, [])

  useEffect(() => {
    // Fetch the redis data for menus
    simpleGet(redisGetURL, { keys: menus.map((menu) => menu.key) }).then(
      (dataStr) => {
        const data = JSON.parse(dataStr)
        const updatedMenus = menus.map((menu) => {
          const value = data[menu.key]
          const selectedItem = menu.items.find((item) => item.value === value)
          return {
            ...menu,
            selectedItem,
          }
        })
        setMenus(updatedMenus)
      }
    )
  }, [])

  const { name } = admin
  const firstName = name ? name.split(" ")[0] : ""
  return (
    <StrictMode>
      {name && (
        <div className="admin-indicator">
          <h3 className="admin-text">Hello {firstName}</h3>
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
  initMenus: PropTypes.array,
  initAdmin: PropTypes.shape({
    username: PropTypes.string,
    email: PropTypes.string,
  }),
  redisGetURL: PropTypes.string,
  authAPIURL: PropTypes.string,
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
