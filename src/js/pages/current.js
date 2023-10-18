import { _getById } from '../modules/utils.js'
import { WebsocketClient } from '../modules/websocket_client.js'

(function () {
  const initEvent = window.APP_DATA.initEvent || null
  if (!initEvent) {
    return
  }
  const location = document.documentElement.dataset.location
  const camera = initEvent.camera_name
  const channel = initEvent.channel_name
  const baseImgURL = window.APP_DATA.imgURL.split('/').slice(0, -1).join('/')
  // eslint-disable-next-line no-unused-vars
  const ws = new WebsocketClient('service', 'channel', location, camera, channel)

  window.addEventListener('channel', (message) => {
    const newEvent = message.data
    const filename = [newEvent.filename, newEvent.ext].join('.')
    _getById('date').textContent = newEvent.day_obs
    _getById('seqNum').textContent = newEvent.seq_num
    _getById('eventName').textContent = filename
    const oldImg = _getById('eventImage')
    const newImg = document.createElement('img')
    const imgURL = `${baseImgURL}/${filename}`
    newImg.src = imgURL
    newImg.id = oldImg.id
    newImg.addEventListener('load', (e) => {
      oldImg.replaceWith(newImg)
      _getById('eventLink').href = imgURL
    })
  })
})()
