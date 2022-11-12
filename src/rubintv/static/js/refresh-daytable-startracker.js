/* eslint-disable quote-props */
/* global jQuery */

import { initTable } from './modules/table-control.js'
import { startrackerDefaultSelected } from './models.js'

(function ($) {
  function starTrackerHtmlInject (htmlParts) {
    $('.channel-day-data').html(htmlParts.table)
  }

  initTable(starTrackerHtmlInject, 5, startrackerDefaultSelected)
})(jQuery)
