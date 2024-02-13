import { WebsocketClient } from '../modules/websocket_client.js'

(function () {
  const locationName = document.documentElement.dataset.locationname
  const camera = window.APP_DATA.camera
  const baseUrl = window.APP_DATA.baseUrl
  if (!window.APP_DATA.ishistorical) {
    const ws = new WebsocketClient()
    ws.subscribe('service', 'camera', locationName, camera.name)
  }
  window.addEventListener('camera', (message) => {
    const currentImage = document.querySelector('.current-still')
    const currentMovie = document.querySelector('.current-movie')

    const newEvent = message.detail.data
    const filename = newEvent.filename
    const seqNum = newEvent.seq_num
    const date = newEvent.day_obs

    let url
    if (newEvent.channel_name === 'stills') {
      url = `${baseUrl}/event_image/${locationName}/${camera.name}/stills/${filename}`
      currentImage.querySelector('img').setAttribute('src', url)
      currentImage.querySelector('a').setAttribute('href', url)
      currentImage.querySelector('.subheader h3').textContent = `${date} : Image ${seqNum}`
      currentImage.querySelector('.desc').textContent = filename
    }
    if (newEvent.channel_name === 'movies') {
      url = `${baseUrl}/event_video/${locationName}/${camera.name}/movies/${filename}`
      const video = currentMovie.querySelector('video')
      const source = video.querySelector('source')
      source.setAttribute('src', url)
      currentMovie.querySelector('.movie-date').textContent = date
      currentMovie.querySelector('.movie-number').textContent = seqNum
      currentMovie.querySelector('.desc').textContent = filename
      video.load()
    }
  })
})()
