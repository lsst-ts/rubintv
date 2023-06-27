import { _getById } from './utils.js'

export function applyYearControls () {
  const years = document.querySelectorAll('.year-title')
  const yearPanels = document.querySelectorAll('.year')
  Array.from(years).forEach(year => {
    year.addEventListener('click', function () {
      if (!this.classList.contains('current')) {
        years.forEach(y => y.classList.remove('current'))
        yearPanels.forEach(y => y.classList.remove('current'))

        const id = `year-${this.dataset.year}`
        const yearPanel = _getById(id)
        this.classList.add('current')
        yearPanel.classList.add('current')
      }
    })
  })
}
