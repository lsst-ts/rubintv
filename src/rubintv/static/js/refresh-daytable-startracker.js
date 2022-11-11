/* eslint-disable quote-props */
/* global jQuery */

import { initTable } from './modules/table-control.js'
import { startrackerDefaultSelected } from './models.js'

(function ($) {
  function starTrackerHtmlInject (htmlParts) {
    $('#per-day-refreshable').html(htmlParts.per_day)
  }

  initTable(starTrackerHtmlInject, 5, startrackerDefaultSelected)
})(jQuery)
