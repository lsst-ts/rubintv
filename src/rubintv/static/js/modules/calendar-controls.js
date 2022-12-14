export function applyYearControls () {
  const years = document.querySelectorAll('.year-title')
  Array.from(years).addEventListener('click', function () {
    const yearPanel = this.closest('.year')
    if (yearPanel.classList.contains('open')) {
      yearPanel.classList.remove('open')
      yearPanel.classList.add('closed')
    } else {
      yearPanel.classList.add('open')
      yearPanel.classList.remove('closed')
    }
  })
}
