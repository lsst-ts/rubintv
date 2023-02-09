import { getJson } from '../modules/utils.js'

window.addEventListener('load', () => {
  const urlPath = document.location.pathname
  const currentImage = document.querySelector('.current-still')
  const currentMovie = document.querySelector('.current-movie')

  setInterval(function refresh () {
    const promise = getJson(urlPath + '/update/image')
    promise.then(data => {
      if (data.channel === 'image') {
        currentImage.querySelector('img').setAttribute('src', data.url)
        currentImage.querySelector('a').setAttribute('href', data.url)
        currentImage.querySelector('.subheader h3').textContent = `${data.date} : Image ${data.seq}`
        currentImage.querySelector('.desc').textContent = data.name
      }
    }).catch(e => {
      console.log('Couldn\'t reach server')
    })
  }, 5000)

  const videoCheckLatest = function () {
    const video = currentMovie.querySelector('video')
    const promise = getJson(urlPath + '/update/movie')
    promise.then(data => {
      const source = video.querySelector('source')
      const currentMovieUrl = source.getAttribute('src')
      if (data.channel === 'movie' && data.url !== currentMovieUrl) {
        source.setAttribute('src', data.url)
        currentMovie.querySelector('.movie-date').textContent(data.date)
        currentMovie.querySelector('.movie-number').textContent(data.seq)
        currentMovie.querySelector('.desc').textContent(data.name)
        video.load()
      }
    }).catch(e => {
      console.log('Couldn\'t reach server')
    })
  }
  setInterval(videoCheckLatest, 5000)
})
