import { _getById, getHtml } from '../modules/utils.js'

window.addEventListener('DOMContentLoaded', function () {
  setInterval(updateEvents, 5000)

  function updateEvents () {
    const theDate = _getById('the-date').dataset.date
    const url = window.location + '/update/' + theDate
    getHtml(url).then(success)
  }

  function success (html) {
    if (html) {
      _getById('night-reports-update').innerHTML = html
    }
  }
})
