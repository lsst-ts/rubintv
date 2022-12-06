/* global jQuery */

(function ($) {
  const theDate = $('[data-date]').attr('data-date')
  const url = window.location + '/update/' + theDate
  setInterval(updateEvents, 5000)

  function updateEvents () {
    $.get(url, success, 'html')
  }

  function success (html) {
    if (html) {
      $('#night-reports-update').html(html)
    }
  }
})(jQuery)
