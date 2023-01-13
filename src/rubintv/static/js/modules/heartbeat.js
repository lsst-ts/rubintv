import { getJson, _getById } from './utils.js'

// heartbeat data structure:
// {
//    "channel": channel,
//    "currTime": currTime,
//    "nextExpected": nextExpected,
//    "errors": {}
// }
// timestamp is seconds since epoch (Jan 1, 1970)

function timestampToDateUTC (timestamp) {
  // Date takes timestamp in milliseconds
  const d = new Date(timestamp * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
  return d
}

export class ChannelStatus {
  // time in secs to try downloading heartbeat again after stale
  NETWORK_ALLOWANCE = 0
  RETRY = 30
  // time in secs to query all blobs to bring in missing services

  constructor (service, dependency = null) {
    this.service = service
    this.dependency = dependency
    this.el = _getById(this.service)
    this.time = 0
    this.next = 0
    this.active = true
    this.updateHeartbeatData()
  }

  updateHeartbeatData () {
    let alive = false

    const promise = getJson(`admin/heartbeat/${this.service}`)

    promise
      .then(heartbeat => {
        this.consumeHeartbeat(heartbeat)
        this.active = this.isActive
        console.log(`found heartbeat for ${this.service}`)
        console.log(`next at ${timestampToDateUTC(this.next)}`)
        alive = true
      })
      .finally(() => {
        this.displayStatus(alive)
        this.waitForNextHeartbeat()
      })
      .catch((e) => {
        console.error(e)
        console.warn(`Couldn't reach server: Unable to retrieve heartbeats for ${this.service}`)
      })
  }

  consumeHeartbeat (heartbeat) {
    this.service = heartbeat.channel
    this.time = heartbeat.currTime
    this.next = heartbeat.nextExpected
    this.errors = heartbeat.errors
  }

  displayStatus (alive = true) {
    // some classes have no display on a page so skip
    // if there's no page element
    if (!this.el) return
    if (alive) {
      this.el.classList.remove('stopped')
      this.el.classList.add(this.status)
    } else {
      this.el.classList.remove('stopped', 'active')
    }
    this.displayHeartbeatInfo()
  }

  displayHeartbeatInfo () {
    const time = this.time
      ? timestampToDateUTC(this.time) + ' UTC'
      : 'never'

    const next = this.active
      ? timestampToDateUTC(this.next)
      : timestampToDateUTC(this.nowTimestamp + this.RETRY)

    const retrying = !this.active ? 'Retrying\n' : ''

    this.el.setAttribute('title', `${retrying}last heartbeat at: ${time}\nnext check at: ${next} UTC`)
  }

  waitForNextHeartbeat () {
    setTimeout(() => {
      this.updateHeartbeatData()
    }, this.nextInterval * 1000)
  }

  get nextInterval () {
    return (this.active)
      ? this.next - this.nowTimestamp
      : this.RETRY
  }

  get isActive () {
    const thisActive = (this.next + this.NETWORK_ALLOWANCE) > this.nowTimestamp
    if (!this.dependency) {
      return thisActive
    }
    return thisActive && this.dependency.isActive
  }

  get status () {
    return this.active ? 'active' : 'stopped'
  }

  get nowTimestamp () {
    return Math.round(Date.now() / 1000)
  }
}
