/* global $ */

export function applyYearControls () {
  $('.year-title').click(function () {
    $(this).parent('.year').toggleClass('open').toggleClass('closed')
  })
}
