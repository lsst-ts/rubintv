/* global jQuery */
import { createTableControlUI, applySelected, loadMetadata } from './modules/table-control.js';

(function ($) {
  const defaultSelected = [
    'exposure_time',
    'observation_type',
    'target_name',
    'filter',
    'disperser',
    'airmass',
    'time_begin_tai'
  ]

  let meta = loadMetadata()
  createTableControlUI(meta, $('.channel-grid-heading'), defaultSelected)
  applySelected(meta, defaultSelected)
  const selected = defaultSelected

  setInterval(function refreshTable () {
    const date = $('.the-date')[0].dataset.date
    const urlPath = document.location.pathname
    $.get(urlPath + '/update/' + date, function (res) {
      $('.channel-day-data').html(res)
    }).done(function () {
      meta = loadMetadata()
      applySelected(meta, selected)
      createTableControlUI(meta, $('.channel-grid-heading'), selected)
    }).fail(function () {
      console.log("Couldn't reach server")
    })
  }, 5000)
})(jQuery)
