/* global jQuery */

(function ($) {
  $('.year-title').click(function () {
    const $yearToOpen = $(this).parent('.year')
    if ($yearToOpen.hasClass('open')) return
    $('.year.open').removeClass('open').addClass('closed')
    $yearToOpen.removeClass('closed').addClass('open')
  })
})(jQuery)
