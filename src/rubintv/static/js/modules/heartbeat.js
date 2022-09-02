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

  displayStatus (alive = true) {
    // channel in this context is the same as channel.prefix used in the template
    const $channelEl = $(`#${this.channel}`)
    if (alive) {
      const status = this.isActive ? 'active' : 'stopped'
      $channelEl.removeClass('stopped').addClass(status)
      console.log(`Channel ${this.channel} is ${status}`)
      console.log(`Last heartbeat from: ${new Date(this.time * 1000)}`)
      const next = this.isActive
        ? new Date(this.next * 1000)
        : new Date((this.nowTimestamp + this.RETRY) * 1000)
      console.log(`Next check at: ${next}`)
      console.log('--------------------')
    } else {
      console.log(`Channel ${this.channel} is unreachable`)
      $channelEl.removeClass('stopped active')
    }
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
