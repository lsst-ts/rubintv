/* global $ */

// heartbeat data structure:
// {
//    "channel": channel,
//    "currTime": currTime,
//    "nextExpected": nextExpected,
//    "errors": {}
// }
// timestamp is seconds since epoch (Jan 1, 1970)

class ChannelStatus {
  // time in secs to try downloading heartbeat again after stale
  RETRY = 120
  // time in secs to query all blobs to bring in missing services

  constructor (heartbeatFromApp) {
    this.consumeHeartbeat(heartbeatFromApp)
    this.url = heartbeatFromApp.url
    this.$el = $(`#${this.channel}`)
    this.displayStatus()
    this.waitForNextHeartbeat()
  }

  get nextInterval () {
    return (this.isActive)
      ? this.next - this.nowTimestamp
      : this.RETRY
  }

  get isActive () {
    return this.next > this.nowTimestamp
  }

  get status () {
    return this.isActive ? 'active' : 'stopped'
  }

  get nowTimestamp () {
    return Math.round(Date.now() / 1000)
  }

  consumeHeartbeat (heartbeat) {
    this.channel = heartbeat.channel
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
    let alive = false
    const self = this
    const urlPath = document.location.pathname
    $.get(`${urlPath}/heartbeat/${this.channel}`, (rawHeartbeat) => {
      if (rawHeartbeat) {
        self.consumeHeartbeat(rawHeartbeat)
        alive = true
      }
    }).always(() => {
      self.displayStatus(alive)
      self.waitForNextHeartbeat()
    })
  }

  displayHeartbeatInfo () {
    const time = this.time
      ? new Date(this.time * 1000).toLocaleString('en-US')
      : 'never'

    const next = this.isActive
      ? new Date(this.next * 1000).toLocaleString('en-US')
      : new Date((this.nowTimestamp + this.RETRY) * 1000).toLocaleString('en-US')

    this.$el.attr({ title: `last heartbeat at: ${time} UTC\nnext check at: ${next} UTC` })
  }

  displayStatus (alive = true) {
    // channel in this context is the same as channel.prefix used in the template
    if (alive) {
      this.$el.removeClass('stopped').addClass(this.status)
    } else {
      this.$el.removeClass('stopped active')
    }
    this.displayHeartbeatInfo()
  }
}

const UPDATE_ALL_AFTER = 6000

const heartbeatsText = document.querySelector('#heartbeats').text
const heartbeats = JSON.parse(heartbeatsText)
let statuses = heartbeats.map(hb => new ChannelStatus(hb))

setInterval(() => {
  const urlPath = document.location.pathname
  $.get(`${urlPath}/heartbeats`, (newHeartbeats) => {
    console.log('Updating all heartbeats')
    newHeartbeats.forEach(hb => {
      console.log(`Found ${hb.channel}`)
    })
    statuses.forEach(hb => { hb.displayStatus(false) })
    statuses = newHeartbeats.map(hb => new ChannelStatus(hb))
  })
}, UPDATE_ALL_AFTER * 1000)
