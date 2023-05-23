import { _elWithAttrs, getHtml, _getById } from '../modules/utils.js'

window.addEventListener('DOMContentLoaded', function () {
  setInterval(function () {
    getHtml(window.location.href).then(htmlString => {
      const temp = _elWithAttrs('div')
      temp.innerHTML = htmlString
      const replacementHtml = temp.querySelector('#refresher').innerHTML
      _getById('refresher').innerHTML = replacementHtml
    })
  }, 5000)
})
