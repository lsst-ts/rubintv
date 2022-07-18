/* global $ */

export function applyYearControls () {
  $('.year-title').click(function () {
    const $yearEl = $(this).parent('.year')
    if ($yearEl.hasClass('open')) {
      $yearEl.removeClass('open').addClass('closed')
    } else {
      $('.year.open').removeClass('open').addClass('closed')
      $yearEl.removeClass('closed').addClass('open')
    }
  })
}
