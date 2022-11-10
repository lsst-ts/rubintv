/* eslint-disable quote-props */
/* global jQuery */

import { initTable } from './modules/table-control.js';

(function ($) {
  const defaultSelected = {
    'Exposure time': '',
    'Image type': '',
    'Target': '',
    'Filter': '',
    'Disperser': '',
    'Airmass': '',
    'TAI': '',
    'DIMM Seeing': ''
  }

  function auxtelHtmlInject (htmlParts) {
    $('#per-day-refreshable').html(htmlParts.per_day)
    $('.channel-day-data').html(htmlParts.table)
  }

  initTable(auxtelHtmlInject, 5, defaultSelected)
})(jQuery)
