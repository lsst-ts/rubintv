import { _getById, _elWithClass } from '../modules/utils'
import { WebsocketClient } from '../modules/ws-service-client'

(function () {
  const initEvent = window.APP_DATA.initEvent || null
  if (!initEvent) {
    return
  }
  const location = document.documentElement.dataset.locationname
  const camera = initEvent.camera_name
  const channel = initEvent.channel_name
  const baseImgURL = window.APP_DATA.imgURL.split('/').slice(0, -1).join('/')
  // eslint-disable-next-line no-unused-vars
  const ws = new WebsocketClient()
  ws.subscribe('service', 'channel', location, camera, channel)

  window.addEventListener('channel', (message) => {
    const newEvent = message.detail.data
    const filename = newEvent.filename
    _getById('date').textContent = newEvent.day_obs
    _getById('seqNum').textContent = newEvent.seq_num
    _getById('eventName').textContent = filename
    const oldImg = _getById('eventImage')
    // create new repsonsive <img> element
    const newImg = _elWithClass('img', 'resp')
    const imgURL = `${baseImgURL}/${filename}`
    newImg.src = imgURL
    newImg.id = oldImg.id
    newImg.addEventListener('load', () => {
      oldImg.replaceWith(newImg)
      _getById('eventLink').href = imgURL
    })
  })
})()
