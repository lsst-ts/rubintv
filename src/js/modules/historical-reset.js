import { simplePost, _getById, _elWithAttrs } from './utils'

export function listenForHistoricalReset () {
  const form = _getById('historicalReset')
  form.addEventListener('click', function (e) {
    e.preventDefault()
    simplePost('api/historical_reset').then(data => {
      const resetForm = _getById('historicalReset')
      resetForm.children[0].disabled = true
      const notice = _elWithAttrs('h3', { text: 'Historical data reloading...' })
      resetForm.after(notice)
    }).catch((err) => {
      console.log(`Couldn't reload historical date: ${err}`)
    })
  })
}
