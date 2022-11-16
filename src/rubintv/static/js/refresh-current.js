/* global jQuery */

(function ($) {
  setInterval(function () {
    $.get(window.location.href, function (html) {
      $('#refresher').replaceWith($(html).find('#refresher'))
    })
  }, 5000)
})(jQuery)
