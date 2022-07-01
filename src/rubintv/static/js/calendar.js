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
  applySelected(meta, defaultSelected, true)
  const selected = defaultSelected

  // click to retrieve & display data for day:
  $('.day').click(function () {
    const date = this.dataset.date
    const urlPath = document.location.pathname

    $.get(urlPath + '/' + date, function (res) {
      $('.channel-day-data').html(res)
    }).done(function () {
      meta = loadMetadata()
      applySelected(meta, selected, true)
      createTableControlUI(meta, $('.channel-grid-heading'), selected)
    }).fail(function () {
      console.log("Couldn't reach server")
    })
  })

  $('.year-title').click(function () {
    const $yearToOpen = $(this).parent('.year')
    if ($yearToOpen.hasClass('open')) return
    $('.year.open').removeClass('open').addClass('closed')
    $yearToOpen.removeClass('closed').addClass('open')
  })
})(jQuery)
