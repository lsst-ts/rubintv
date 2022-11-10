/* eslint-disable quote-props */
/* global jQuery */

import { initTable } from './modules/table-control.js';

(function ($) {
  const defaultSelected = {
    'Alt': 'group-a',
    'Az': 'group-a',
    'Rot': 'group-a',
    'Delta Alt': 'b',
    'Delta Az': 'b',
    'Delta Rot': 'b'
  }

  function starTrackerHtmlInject (htmlParts) {
    $('#per-day-refreshable').html(htmlParts.per_day)
  }

  initTable(starTrackerHtmlInject, 5, defaultSelected)
})(jQuery)
