import { getJson, _getById } from './utils.js'

// heartbeat data structure:
// {
//    "channel": channel,
//    "currTime": currTime,
//    "nextExpected": nextExpected,
//    "errors": {}
// }
// timestamp is seconds since epoch (Jan 1, 1970)

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
    this.updateHeartbeatData()
  }

  get nextInterval () {
    return (this.isActive)
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
    return this.isActive ? 'active' : 'stopped'
  }

  get nowTimestamp () {
    return Math.round(Date.now() / 1000)
  }

  consumeHeartbeat (heartbeat) {
    this.service = heartbeat.channel
    this.time = heartbeat.currTime
    this.next = heartbeat.nextExpected
    this.errors = heartbeat.errors
  }

  waitForNextHeartbeat () {
    setTimeout(() => {
      this.updateHeartbeatData()
    }, this.nextInterval * 1000)
  }

  updateHeartbeatData () {
    this.alive = false
    const self = this

    const promise = getJson(`admin/heartbeat/${this.service}`)
    promise.then(heartbeat => {
      if (Object.keys(heartbeat).length > 0) {
        self.consumeHeartbeat(heartbeat)
        this.alive = true
      }
    }).finally(() => {
      self.displayStatus(this.alive)
      self.waitForNextHeartbeat()
    }).catch((e) => {
      console.warn("Couldn't reach server: Unable to retrieve heartbeats")
    })
  }

  displayHeartbeatInfo () {
    const time = this.time
      ? new Date(this.time * 1000).toLocaleString('en-US', { timeZone: 'UTC' }) + ' UTC'
      : 'never'

    const next = this.isActive
      ? new Date(this.next * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
      : new Date((this.nowTimestamp + this.RETRY) * 1000).toLocaleString('en-US', { timeZone: 'UTC' }) + ' retrying'

    this.el.setAttribute('title', `last heartbeat at: ${time}\nnext check at: ${next} UTC`)
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
}
