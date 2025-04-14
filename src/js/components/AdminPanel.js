import React, { useState, useEffect } from "react"
// Change the import to use the default export if Modal is the default export
import { useModal, ConfirmationModal, ModalProvider } from "./Modal"
import { simplePost, simpleGet } from "../modules/utils"
import PropTypes from "prop-types"

// Custom hook to handle Redis post success/failure
function useRedisStatus() {
  const [redisChanged, setRedisChanged] = useState(null)

  const updateRedisStatus = (status) => {
    setRedisChanged(status)
    setTimeout(() => {
      setRedisChanged(null)
    }, 2000)
  }

  return [redisChanged, updateRedisStatus]
}

export default function AdminPanels({
  initMenus,
  initAdmin,
  redisGetURL,
  authAPIURL,
}) {
  const [admin, setAdmin] = useState(initAdmin)
  const [menus, setMenus] = useState(initMenus)

  const refreshMenus = () => {
    simpleGet(redisGetURL, { keys: menus.map((menu) => menu.key) }).then(
      (dataStr) => {
        const data = JSON.parse(dataStr)
        const updatedMenus = menus.map((menu) => {
          const value = data[menu.key]
          const selectedItem = menu.items.find((item) => item.value === value)
          const updatedMenu = {
            ...menu,
            selectedItem,
          }
          return updatedMenu
        })
        setMenus(updatedMenus)
      }
    )
  }

  useEffect(() => {
    simpleGet(authAPIURL)
      .then((dataStr) => {
        try {
          JSON.parse(dataStr)
        } catch (e) {
          console.error("Error parsing auth api JSON response:", e)
          return
        }
        const data = JSON.parse(dataStr)
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
      .catch((error) => {
        console.warn("Error loading auth API:", error.message)
      })
  }, [])

  const { name } = admin
  const firstName = name ? name.split(" ")[0] : ""

  return (
    <>
      {name && (
        <div className="admin-panels-header">
          <h3 className="admin-greeting">Hello {firstName}</h3>
        </div>
      )}
      <h2>Settings</h2>
      <RedisPanel menus={menus} setMenus={setMenus} redisGetURL={redisGetURL} />
      <ModalProvider>
        <AdminDangerPanel refreshMenus={refreshMenus} />
      </ModalProvider>
    </>
  )
}

AdminPanels.propTypes = {
  initMenus: PropTypes.array,
  initAdmin: PropTypes.shape({
    username: PropTypes.string,
    email: PropTypes.string,
    name: PropTypes.string,
  }),
  redisGetURL: PropTypes.string,
  authAPIURL: PropTypes.string,
}

export function RedisPanel({ menus, setMenus, redisGetURL }) {
  const [refresh, setRefresh] = useState(false)

  const fetchMenus = () => {
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
  }

  useEffect(() => {
    fetchMenus()
  }, [refresh, redisGetURL]) // Trigger fetch only when `refresh` changes

  const triggerRefresh = () => setRefresh((prev) => !prev)

  const handleItemSelect = (menuKey, item) => {
    const { value } = item
    simplePost("api/redis_post", { key: menuKey, value })
      .then(() => {
        console.log("Redis updated successfully")
      })
      .catch((error) => {
        console.error("Error posting to redis:", error)
      })
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-part">
        {menus.map((menu, index) => (
          <DropDownMenu
            key={index}
            menu={menu}
            onItemSelect={(item) => handleItemSelect(menu.key, item)}
          />
        ))}
      </div>
      <div className="admin-panel-part">
        <AdminSendRedisCommand triggerRefresh={triggerRefresh} />
      </div>
    </div>
  )
}

RedisPanel.propTypes = {
  menus: PropTypes.array.isRequired,
  setMenus: PropTypes.func.isRequired,
  redisGetURL: PropTypes.string.isRequired,
}

export function DropDownMenu({ menu, onItemSelect }) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(menu.selectedItem)

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

    return () => {
      window.removeEventListener("click", handleClickOutside)
    }
  }, [isOpen])

  const handleItemSelect = (item) => {
    setSelectedItem(item)
    setIsOpen(false)
    if (onItemSelect) {
      onItemSelect(item) // Notify parent about the selected item
    }
  }

  const menuClass = isOpen ? "dropdown-menu" : "dropdown-menu hidden"
  const selectedTitle = selectedItem ? selectedItem.title : "- Select -"
  const selectedClass = selectedItem
    ? "dropdown-button"
    : "dropdown-button greyed-out"

  return (
    <div className="menu box">
      <div className="menu-header box-header">
        <h4 className="menu-title box-title">{menu.title}</h4>
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
  menu: PropTypes.object.isRequired,
  onItemSelect: PropTypes.func, // Callback for item selection
}

export function AdminSendRedisCommand({ triggerRefresh }) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()

  const successClass =
    redisChanged !== null ? (redisChanged ? "success" : "fail") : ""

  return (
    <div className="redis-command-panel box">
      <div className="redis-command-header box-header">
        <h4 className="redis-command-title box-title">Redis Command</h4>
        <span className={successClass}></span>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          const key = e.target.elements.key.value
          const value = e.target.elements.value.value
          simplePost("api/redis_post", { key, value })
            .then(() => {
              updateRedisStatus(true)
              if (triggerRefresh) {
                triggerRefresh()
              }
            })
            .catch((error) => {
              updateRedisStatus(false)
              console.error("Error posting to redis:", error)
            })
        }}
      >
        <div className="form-group">
          <label htmlFor="key">Key:</label>
          <input type="text" id="key" name="key" placeholder="Key" required />
        </div>
        <div className="form-group">
          <label htmlFor="value">Value:</label>
          <input
            type="text"
            id="value"
            name="value"
            placeholder="Value"
            required
          />
        </div>
        <button type="submit">Send</button>
      </form>
    </div>
  )
}

AdminSendRedisCommand.propTypes = {
  triggerRefresh: PropTypes.func,
}

export function AdminDangerPanel({ refreshMenus }) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()
  const { showModal } = useModal()
  const successClass =
    redisChanged !== null ? (redisChanged ? "success" : "fail") : ""

  const clearRedis = () => {
    simplePost("api/redis_post", { key: "clear_redis", value: "true" })
      .then(() => {
        updateRedisStatus(true)
        if (refreshMenus) {
          refreshMenus()
        }
      })
      .catch((error) => {
        updateRedisStatus(false)
        console.error("Error posting to redis:", error)
      })
  }

  const handleClick = (e) => {
    e.preventDefault()

    showModal(
      <ConfirmationModal
        title="Clear Redis"
        message="Are you sure you want to clear Redis?"
        onConfirm={() => {
          clearRedis()
          showModal(null) // Close the modal after confirmation
        }}
        onCancel={() => {
          showModal(null) // Close the modal after cancellation
        }}
      />
    )
  }

  return (
    <div className="admin-panel danger">
      <div className="admin-panel-part">
        <div className="admin-header box">
          <div className="admin-header box-header">
            <h4 className="admin-title box-title">Clear Redis</h4>
            <span className={successClass}></span>
          </div>

          <button className="danger-button" onClick={handleClick}>
            Clear Redis
          </button>
        </div>
      </div>
    </div>
  )
}

AdminDangerPanel.propTypes = {
  redisChanged: PropTypes.bool,
  refreshMenus: PropTypes.func,
}
AdminDangerPanel.defaultProps = {
  redisChanged: null,
  refreshMenus: null,
}
