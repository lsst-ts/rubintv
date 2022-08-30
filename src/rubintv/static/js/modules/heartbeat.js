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
  RETRY = 120

  constructor (heartbeatFromApp) {
    this.consumeHeartbeat(heartbeatFromApp)
    this.url = heartbeatFromApp.url
    this.displayStatus()
    this.waitForNextHeartbeat()
  }

  get nextInterval () {
    return (this.isActive())
      ? (this.next - this.nowTimestamp()) + this.TOLERANCE
      : this.RETRY
  }

  get isActive () {
    return this.next < (this.nowTimestamp() + this.TOLERANCE)
  }

  consumeHeartbeat (heartbeat) {
    this.channel = heartbeat.channel
    this.time = heartbeat.currTime
    this.next = heartbeat.nextExpected
    this.errors = heartbeat.errors
  }

  waitForNextHeartbeat () {
    setTimeout(this.updateHeartbeatData, this.nextInterval())
  }

  updateHeartbeatData () {
    $.get(this.url, (rawHeartbeat) => {
      this.consumeHeartbeat(rawHeartbeat)
      this.displayStatus()
      this.waitForNextHeartbeat()
    })
  }

  nowTimestamp () {
    return Math.round(Date.now() / 1000)
  }

  displayStatus () {
    const status = this.isActive() ? 'active' : 'stopped'
    // channel in this context is the same as channel.prefix used in the template
    const $channelEl = $(`#${this.channel}`)
    $channelEl.removeClass('stopped')
    $channelEl.addClass(status)
    console.log(`Channel ${this.channel} is ${status}`);
    console.log(`Last heartbeat from: ${new Date(this.time)}`);
    console.log(`Next check at: ${new Date(this.next)}`);
  }
}

const heartbeatsText = document.querySelector('#heartbeats').text
const heartbeats = JSON.parse(heartbeatsText)
heartbeats.map(hb => new ChannelStatus(hb))
