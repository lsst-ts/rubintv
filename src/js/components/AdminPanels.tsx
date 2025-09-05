import React, { useState, useEffect } from "react"
import DropDownMenu from "./DropDownMenu"
import { useModal, ConfirmationModal, ModalProvider } from "./Modal"
import { simplePost, simpleGet } from "../modules/utils"
import { Menu, MenuItem } from "./DropDownMenu"

export interface AdminInfo {
  username?: string
  email?: string
  name?: string
}

interface AdminPanelsProps {
  initMenus: Menu[]
  initAdmin: AdminInfo
  redisEndpointUrl: string
  redisKeyPrefix: (key: string) => string
  authEndpointUrl: string
}

interface RedisPanelProps {
  menus: Menu[]
  setMenus: (menus: Menu[]) => void
  redisEndpointUrl: string
  redisKeyPrefix: (key: string) => string
}

interface DropDownMenuContainerProps {
  menu: Menu
  onItemSelect: (item: MenuItem) => Promise<void>
}

interface AdminSendRedisValueProps {
  redisEndpointUrl: string
  redisKeyPrefix: (key: string) => string
  keyToSend: string
  valueToSend?: string | null
  title?: string
  size?: string
  requiresConfirmation?: boolean
}

interface AdminSendRedisCommandProps {
  redisEndpointUrl: string
  redisKeyPrefix: (key: string) => string
}

// Custom hook to handle Redis post success/failure
function useRedisStatus(): [string | null, (status: string) => void] {
  const [redisChanged, setRedisChanged] = useState<string | null>(null)

  const updateRedisStatus = (status: string) => {
    setRedisChanged(status)
    // Only auto-clear if status is "true" or "false"
    if (status === "true" || status === "false") {
      setTimeout(() => setRedisChanged(null), 2000)
    }
  }

  return [redisChanged, updateRedisStatus]
}

export default function AdminPanels({
  initMenus,
  initAdmin,
  redisEndpointUrl,
  redisKeyPrefix,
  authEndpointUrl,
}: AdminPanelProps) {
  const [admin, setAdmin] = useState(initAdmin)
  const [menus, setMenus] = useState(initMenus)

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
        } catch (error) {
          console.error("Error parsing auth API JSON response:", error)
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
            <AdminDangerPanel redisEndpointUrl={redisEndpointUrl} />
          </div>
        </div>
      </div>
    </ModalProvider>
  )
}

export function RedisPanel({
  menus,
  redisEndpointUrl,
  redisKeyPrefix,
}: RedisPanelProps) {
  const handleItemSelect = async (menuKey: string, item: MenuItem) => {
    try {
      await simplePost(redisEndpointUrl, { key: menuKey, value: item.value })
      console.log("Redis updated successfully")
    } catch (error) {
      console.error("Error posting to redis:", error)
      throw error
    }
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-part">
        {menus.map((menu, index) => (
          <DropDownMenuContainer
            key={index}
            menu={menu}
            onItemSelect={(item) => handleItemSelect(menu.key, item)}
          />
        ))}
      </div>
      <div className="admin-panel-part">
        <AdminSendRedisCommand
          redisEndpointUrl={redisEndpointUrl}
          redisKeyPrefix={redisKeyPrefix}
        />
        <AdminSendRedisValue
          redisEndpointUrl={redisEndpointUrl}
          redisKeyPrefix={redisKeyPrefix}
          keyToSend="WITNESS_DETECTOR"
          title="Witness Detector"
        />
      </div>
      <div className="admin-panel-part">
        <AdminSendRedisValue
          redisEndpointUrl={redisEndpointUrl}
          redisKeyPrefix={redisKeyPrefix}
          keyToSend="RESET_HEAD_NODE"
          valueToSend="1"
          title="Reset Head Node"
          size="small"
          requiresConfirmation={true}
        />
      </div>
    </div>
  )
}

export function DropDownMenuContainer({
  menu,
  onItemSelect,
}: DropDownMenuContainerProps) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()
  const [thisMenu, setThisMenu] = useState(menu)

  const handleSelect = (item: MenuItem) => {
    updateRedisStatus("pending")
    onItemSelect(item)
      .then(() => {
        updateRedisStatus("true")
        setThisMenu((prevMenu: Menu) => ({
          ...prevMenu,
          selectedItem: item,
        }))
      })
      .catch((error) => {
        console.error("Error selecting item:", error)
        updateRedisStatus("false")
        setThisMenu((prevMenu) => ({
          ...prevMenu,
          selectedItem: null,
        }))
      })
  }

  return (
    <div className="dropdown-menu-container box">
      <div className="dropdown-menu-header box-header">
        <h4 className="dropdown-menu-title box-title">{menu.title}</h4>
        <StatusIndicator status={redisChanged} />
      </div>
      <DropDownMenu menu={thisMenu} onItemSelect={handleSelect} />
    </div>
  )
}

export function AdminSendRedisValue({
  redisEndpointUrl,
  redisKeyPrefix,
  title = "Send Redis Value",
  keyToSend,
  valueToSend = null,
  size = "",
  requiresConfirmation = false,
}: AdminSendRedisValueProps) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()
  const { showModal } = useModal()

  const handleConfirmSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    showModal(
      <ConfirmationModal
        title={title}
        message={`Are you sure you want to send value "${valueToSend}" to key "${keyToSend}"?`}
        onConfirm={() => {
          handleSubmit(e)
          showModal(null)
        }}
        onCancel={() => showModal(null)}
      />
    )
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    updateRedisStatus("pending")
    const key = redisKeyPrefix(keyToSend)
    const form = e.target as HTMLFormElement
    const valueInput = form.elements.namedItem("value") as HTMLInputElement
    const value = valueInput.value
    simplePost(redisEndpointUrl, { key, value })
      .then(() => {
        updateRedisStatus("true")
      })
      .catch((error) => {
        updateRedisStatus("false")
        console.error("Error posting to redis:", error)
      })
  }

  const handleClick = requiresConfirmation ? handleConfirmSubmit : handleSubmit

  return (
    <div className={`redis-command-panel box ${size}`}>
      <div className="redis-command-header box-header">
        <h4 className="redis-command-title box-title">{title}</h4>
        <StatusIndicator status={redisChanged} />
      </div>
      <form onSubmit={handleClick}>
        <div className="form-group">
          <label htmlFor="value">Value:</label>
          {!valueToSend && (
            <input
              type="text"
              id="value"
              name="value"
              placeholder="Value"
              required
            />
          )}
          {valueToSend && (
            <input type="hidden" id="value" name="value" value={valueToSend} />
          )}
        </div>
        <button type="submit">Send</button>
      </form>
    </div>
  )
}

export function AdminSendRedisCommand({
  redisEndpointUrl,
  redisKeyPrefix,
}: AdminSendRedisCommandProps) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    updateRedisStatus("pending")
    const form = e.target as HTMLFormElement
    const keyInput = form.elements.namedItem("key") as HTMLInputElement
    const valueInput = form.elements.namedItem("value") as HTMLInputElement
    const key = redisKeyPrefix(keyInput.value)
    const value = valueInput.value
    simplePost(redisEndpointUrl, { key, value })
      .then(() => {
        updateRedisStatus("true")
      })
      .catch((error) => {
        updateRedisStatus("false")
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

export function AdminDangerPanel({
  redisEndpointUrl,
}: {
  redisEndpointUrl: string
}) {
  const [redisChanged, updateRedisStatus] = useRedisStatus()
  const { showModal } = useModal()

  const clearRedis = () => {
    updateRedisStatus("pending") // set pending state
    simplePost(redisEndpointUrl, { key: "clear_redis", value: "true" })
      .then(() => {
        updateRedisStatus("true")
      })
      .catch((error) => {
        updateRedisStatus("false")
        console.error("Error posting to redis:", error)
      })
  }

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
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

export function StatusIndicator({ status }: { status: string | null }) {
  const statusClass = (status: string | null) => {
    switch (status) {
      case "true":
        return "indicator-success"
      case "false":
        return "indicator-fail"
      case "pending":
        return "indicator-pending"
      default:
        return "indicator"
    }
  }
  return (
    <div className={statusClass(status)}>
      <span className="status-icon">●</span>
    </div>
  )
}
