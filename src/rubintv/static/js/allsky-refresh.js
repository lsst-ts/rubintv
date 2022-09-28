/* global jQuery */
import { ChannelStatus } from './modules/heartbeat.js'

(function ($) {
  const urlPath = document.location.pathname
  const currentImage = $('.current-still')
  const currentMovie = $('.current-movie')

  setInterval(function refresh () {
    $.get(urlPath + '/update/image', function (data) {
      if (data.channel === 'image') {
        currentImage.find('img').attr({ src: data.url })
        currentImage.find('a').attr({ href: data.url })
        currentImage.find('.subheader h3').text(`${data.date} : Image ${data.seq}`)
        currentImage.find('.desc').text(data.name)
      }
    })
  }, 5000)

  const videoCheckLatest = function () {
    const video = currentMovie.find('video')[0]
    $.get(urlPath + '/update/monitor', function (data) {
      const currentMovieUrl = $(video).find('source').attr('src')
      if (data.channel === 'monitor' && data.url !== currentMovieUrl) {
        $(video).find('source').attr({ src: data.url })
        currentMovie.find('.movie-date').text(data.date)
        currentMovie.find('.movie-number').text(data.seq)
        currentMovie.find('.desc').text(data.name)
        video.load()
      }
    })
  }
  setInterval(videoCheckLatest, 5000)

  const status = new ChannelStatus('allsky')
  console.log(JSON.stringify(status))
})(jQuery)
