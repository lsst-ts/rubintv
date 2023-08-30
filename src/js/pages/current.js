import { _elWithAttrs, getJson, _getById } from '../modules/utils.js'

window.addEventListener('DOMContentLoaded', function () {
  const url = window.location.href + '_update'
  const dateEl = _getById('date')
  const seqEl = _getById('seqNum')
  const eventLink = _getById('eventLink')
  let currentSeq = parseInt(seqEl.innerText)
  let currentDate = dateEl.innerText
  let eventImage = _getById('eventImage')
  setInterval(function () {
    getJson(url).then(data => {
      if (data.seqNum !== currentSeq || data.date !== currentDate) {
        currentSeq = data.seqNum
        currentDate = data.date
        seqEl.textContent = currentSeq
        dateEl.textContent = currentDate
        eventLink.href = data.url
        const newEventImage = _elWithAttrs('img', {
          id: 'eventImage',
          class: 'resp',
          src: data.url
        })
        newEventImage.addEventListener('load', (e) => {
          eventImage.replaceWith(newEventImage)
          eventImage = _getById('eventImage')
        })
      }
    })
  }, 5000)
})
