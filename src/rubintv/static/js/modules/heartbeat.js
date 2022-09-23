/* global $ */

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
  RETRY = 120
  // time in secs to query all blobs to bring in missing services

  constructor (service, dependency = null) {
    this.service = service
    this.dependency = dependency
    this.$el = $(`#${this.service}`)
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
    const thisActive = this.next > this.nowTimestamp
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

    $.get(`admin/heartbeat/${this.service}`, (heartbeat) => {
      if (!$.isEmptyObject(heartbeat)) {
        self.consumeHeartbeat(heartbeat)
        this.alive = true
      }
    }).always(() => {
      self.displayStatus(this.alive)
      self.waitForNextHeartbeat()
    })
  }

  displayHeartbeatInfo () {
    const time = this.time
      ? new Date(this.time * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
      : 'never'

    const next = this.isActive
      ? new Date(this.next * 1000).toLocaleString('en-US', { timeZone: 'UTC' })
      : new Date((this.nowTimestamp + this.RETRY) * 1000).toLocaleString('en-US', { timeZone: 'UTC' })

    this.$el.attr({ title: `last heartbeat at: ${time} UTC\nnext check at: ${next} UTC` })
  }

  displayStatus (alive = true) {
    if (alive) {
      this.$el.removeClass('stopped').addClass(this.status)
    } else {
      this.$el.removeClass('stopped active')
    }
    this.displayHeartbeatInfo()
  }
}
