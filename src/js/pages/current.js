import { _elWithAttrs, getJson, _getById } from '../modules/utils.js'

window.addEventListener('DOMContentLoaded', function () {
  const url = window.location.href + "_update"
  const dateEl = _getById("date")
  const seqEl = _getById("seqNum")
  const eventLink = _getById("eventLink")
  const eventImage = _getById("eventImage")
  let currentSeq = parseInt(seqEl.innerText)
  let currentDate = dateEl.innerText
  setInterval(function () {
    getJson(url).then(data => {
      if (data.seqNum !== currentSeq || data.date !== currentDate) {
        currentSeq = data.seqNum
        currentDate = data.date
        seqEl.textContent = currentSeq
        dateEl.textContent = currentDate
        eventLink.href = data.url
        const newEventImage = _elWithAttrs("img", {
          id: "eventImage",
          class: "resp",
          src: data.url
        })
        newEventImage.addEventListener('load', (e) => {
          eventImage.replaceWith(newEventImage)
        })
      }
    })
  }, 5000)
})
