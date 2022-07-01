/* global jQuery */

(function ($) {
  setTimeout(function () {
    $('#refresher').load(window.location.href + ' #refresher')
  }, 5000)
})(jQuery)
