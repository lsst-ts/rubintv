/* global jQuery */

(function ($) {
  setInterval(function () {
    $('#refresher').load(window.location.href + ' #refresher')
  }, 5000)
})(jQuery)
