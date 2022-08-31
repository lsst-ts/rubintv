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
  // allowable time for network/other tardiness in seconds
  TOLERANCE = 5
  // time in secs to try downloading heartbeat again after stale
  RETRY = 60

  constructor (heartbeatFromApp) {
    this.consumeHeartbeat(heartbeatFromApp)
    this.url = heartbeatFromApp.url
    this.displayStatus()
    this.waitForNextHeartbeat()
  }

  get nextInterval () {
    return (this.isActive)
      ? ((this.next - this.nowTimestamp) + this.TOLERANCE)
      : this.RETRY
  }

  get isActive () {
    return this.next > (this.nowTimestamp + this.TOLERANCE)
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
    console.log(`interval set for ${this.nextInterval} seconds`)
  }

  updateHeartbeatData () {
    const self = this
    $.get(this.url, (rawHeartbeat) => {
      self.consumeHeartbeat(rawHeartbeat)
    }).always(() => {
      self.displayStatus()
      self.waitForNextHeartbeat()
    })
  }

  displayStatus () {
    const status = this.isActive ? 'active' : 'stopped'
    // channel in this context is the same as channel.prefix used in the template
    const $channelEl = $(`#${this.channel}`)
    $channelEl.removeClass('stopped')
    $channelEl.addClass(status)
    console.log(`Channel ${this.channel} is ${status}`)
    console.log(`Last heartbeat from: ${new Date(this.time * 1000)}`)
    const next = this.isActive
      ? new Date(this.next * 1000)
      : new Date((this.nowTimestamp + this.RETRY) * 1000)
    console.log(`Next check at: ${next}`)
  }
}

const heartbeatsText = document.querySelector('#heartbeats').text
const heartbeats = JSON.parse(heartbeatsText)
heartbeats.map(hb => new ChannelStatus(hb))
