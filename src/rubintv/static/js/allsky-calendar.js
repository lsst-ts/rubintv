/* global jQuery */

(function ($) {
  // click to retrieve & display data for day:
  $('.day').click(function () {
    const date = this.dataset.date
    const urlPath = document.location.pathname
    $('.current-movie').load(urlPath + '/' + date)
  })
  $('.year-title').click(function () {
    const $yearToOpen = $(this).parent('.year')
    if ($yearToOpen.hasClass('open')) return
    $('.year.open').removeClass('open').addClass('closed')
    $yearToOpen.removeClass('closed').addClass('open')
  })
})(jQuery)
