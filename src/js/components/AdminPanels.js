import React, { useState, useEffect } from "react"
import DropDownMenu from "./DropDownMenu"
import { useModal, ConfirmationModal, ModalProvider } from "./Modal"
import { simplePost, simpleGet } from "../modules/utils"
import PropTypes from "prop-types"

// Utility function to fetch and update menus
const fetchAndUpdateMenus = (redisEndpointUrl, menus, setMenus) => {
  simpleGet(redisEndpointUrl, { keys: menus.map((menu) => menu.key) }).then(
    (dataStr) => {
      const data = JSON.parse(dataStr)
      const updatedMenus = menus.map((menu) => {
        const value = data[menu.key]
        const selectedItem = menu.items.find((item) => item.value === value)
        return { ...menu, selectedItem }
      })
      setMenus(updatedMenus)
    }
  )
}

// Custom hook to handle Redis post success/failure
function useRedisStatus() {
  const [redisChanged, setRedisChanged] = useState(null)

  const updateRedisStatus = (status) => {
    setRedisChanged(status)
    setTimeout(() => setRedisChanged(null), 2000)
  }

  return [redisChanged, updateRedisStatus]
}

export default function AdminPanels({
  initMenus,
  initAdmin,
  redisEndpointUrl,
  redisKeyPrefix,
  authEndpointUrl,
}) {
  const [admin, setAdmin] = useState(initAdmin)
  const [menus, setMenus] = useState(initMenus)

  const refreshMenus = () =>
    fetchAndUpdateMenus(redisEndpointUrl, menus, setMenus)

  useEffect(() => {
    simpleGet(authEndpointUrl)
      .then((dataStr) => {
        try {
          const data = JSON.parse(dataStr)
          setAdmin((prevAdmin) => ({
            ...prevAdmin,
            email: data.email,
            name: data.name,
          }))
        } catch (e) {
          console.error("Error parsing auth API JSON response:", e)
        }
      })
      .catch((error) => console.warn("Error loading auth API:", error.message))
  }, [])

  const firstName = admin.name ? admin.name.split(" ")[0] : ""

  return (
    <ModalProvider>
      {admin.name && <h3 className="admin-greeting">Hello {firstName}</h3>}
      <div className="admin-panels-container">
        <div className="admin-panels-header">
          <h3 className="admin-panels-title">Redis Controls</h3>
        </div>
        <RedisPanel
          menus={menus}
          setMenus={setMenus}
          redisEndpointUrl={redisEndpointUrl}
          redisKeyPrefix={redisKeyPrefix}
        />
        <div className="danger-panel">
          <div className="danger-panel-border">
            <h4 className="danger-panel-title">Danger Zone</h4>
            <AdminDangerPanel
              refreshMenus={refreshMenus}
              redisEndpointUrl={redisEndpointUrl}
            />
          </div>
        </div>
      </div>
    </ModalProvider>
  )
}
AdminPanels.propTypes = {
  initMenus: PropTypes.array,
  initAdmin: PropTypes.shape({
    username: PropTypes.string,
    email: PropTypes.string,
    name: PropTypes.string,
  }),
  redisEndpointUrl: PropTypes.string,
  redisKeyPrefix: PropTypes.func,
  authEndpointUrl: PropTypes.string,
}

export function RedisPanel({
  menus,
  setMenus,
  redisEndpointUrl,
  redisKeyPrefix,
}) {
  const handleRefresh = () => {
    fetchAndUpdateMenus(redisEndpointUrl, menus, setMenus)
  }

  useEffect(() => {
    handleRefresh()
  }, [redisEndpointUrl])

  const handleItemSelect = (menuKey, item) => {
    return simplePost(redisEndpointUrl, { key: menuKey, value: item.value })
      .then(() => console.log("Redis updated successfully"))
      .catch((error) => console.error("Error posting to redis:", error))
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-part">
        {menus.map((menu, index) => (
          <DropDownMenuContainer
            key={index}
            menu={menu}
            onItemSelect={(item) => handleItemSelect(menu.key, item)}
            redisEndpointUrl={redisEndpointUrl}
          />
        ))}
      </div>
      <div className="admin-panel-part">
        <AdminSendRedisCommand
          onRefresh={handleRefresh}
          redisEndpointUrl={redisEndpointUrl}
          redisKeyPrefix={redisKeyPrefix}
        />
      </div>
    </div>
  )
}
RedisPanel.propTypes = {
  menus: PropTypes.array.isRequired,
  setMenus: PropTypes.func.isRequired,
  redisEndpointUrl: PropTypes.string.isRequired,
  redisKeyPrefix: PropTypes.func.isRequired,
}

export function DropDownMenuContainer({ menu, onItemSelect }) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()

  const handleSelect = (item) => {
    onItemSelect(item)
      .then(() => {
        updateRedisStatus(true)
      })
      .catch((error) => {
        console.error("Error selecting item:", error)
        updateRedisStatus(false)
      })
  }

  return (
    <div className="dropdown-menu-container box">
      <div className="dropdown-menu-header box-header">
        <h4 className="dropdown-menu-title box-title">{menu.title}</h4>
        <StatusIndicator status={redisChanged} />
      </div>
      <DropDownMenu menu={menu} onItemSelect={handleSelect} />
    </div>
  )
}
DropDownMenuContainer.propTypes = {
  menu: PropTypes.object.isRequired,
  onItemSelect: PropTypes.func.isRequired,
}

export function AdminSendRedisCommand({
  onRefresh,
  redisEndpointUrl,
  redisKeyPrefix,
}) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()

  const handleSubmit = (e) => {
    e.preventDefault()
    const key = redisKeyPrefix(e.target.elements.key.value)
    const value = e.target.elements.value.value
    simplePost(redisEndpointUrl, { key, value })
      .then(() => {
        updateRedisStatus(true)
        if (onRefresh) onRefresh()
      })
      .catch((error) => {
        updateRedisStatus(false)
        console.error("Error posting to redis:", error)
      })
  }

  return (
    <div className="redis-command-panel box">
      <div className="redis-command-header box-header">
        <h4 className="redis-command-title box-title">Redis Command</h4>
        <StatusIndicator status={redisChanged} />
      </div>
      <form onSubmit={handleSubmit}>
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
  onRefresh: PropTypes.func,
  redisEndpointUrl: PropTypes.string.isRequired,
  redisKeyPrefix: PropTypes.func.isRequired,
}

export function AdminDangerPanel({ refreshMenus, redisEndpointUrl }) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()
  const { showModal } = useModal()

  const clearRedis = () => {
    simplePost(redisEndpointUrl, { key: "clear_redis", value: "true" })
      .then(() => {
        updateRedisStatus(true)
        if (refreshMenus) refreshMenus()
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
          showModal(null)
        }}
        onCancel={() => showModal(null)}
      />
    )
  }

  return (
    <div className="admin-panel-part">
      <div className="admin-header box">
        <div className="admin-header box-header">
          <h4 className="admin-title box-title">Clear Redis</h4>
          <StatusIndicator status={redisChanged} />
        </div>
        <button className="danger-button" onClick={handleClick}>
          Clear Redis
        </button>
      </div>
    </div>
  )
}
AdminDangerPanel.propTypes = {
  redisEndpointUrl: PropTypes.string.isRequired,
  refreshMenus: PropTypes.func,
}

export function StatusIndicator({ status }) {
  return (
    <div
      className={
        status !== null
          ? status
            ? "success indicator"
            : "fail indicator"
          : "indicator"
      }
    >
      <span className="status-icon">●</span>
    </div>
  )
}
StatusIndicator.propTypes = {
  status: PropTypes.bool,
}
