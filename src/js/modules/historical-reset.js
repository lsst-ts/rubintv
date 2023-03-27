import { simplePost, _getById } from './utils.js'

export function listenForHistoricalReset () {
  const form = _getById('historicalReset')
  form.addEventListener('click', function (e) {
    e.preventDefault()
    // hide 'done' in case button is pressed again
    form.querySelector('.done').classList.add('hidden')
    form.querySelector('.pending').classList.remove('hidden')

    simplePost('reload_historical').then(data => {
      console.log(`${data}: reload success`)
      form.querySelector('.pending').classList.add('hidden')
      form.querySelector('.done').classList.remove('hidden')
    }).catch((err) => {
      console.log(`Couldn't reload historical date: ${err}`)
    })
  })
}
