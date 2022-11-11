/* global jQuery */
import { initTable } from './modules/table-control.js'
import { auxtelDefaultSelected } from './models.js'

(function ($) {
  function auxtelHtmlInject (htmlParts) {
    $('#per-day-refreshable').html(htmlParts.per_day)
    $('.channel-day-data').html(htmlParts.table)
  }

  initTable(auxtelHtmlInject, 5, auxtelDefaultSelected)
})(jQuery)
