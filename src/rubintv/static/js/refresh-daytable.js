/* global jQuery */
import { createTableControlUI, applySelected, parseJsonFromDOM, DefaultSelected } from './modules/table-control.js';

(function ($) {
  let meta = parseJsonFromDOM('#table-metadata')
  createTableControlUI(meta, $('#table-controls'), DefaultSelected)
  applySelected(meta, DefaultSelected)
  const selected = DefaultSelected

  setInterval(function refreshTable () {
    const date = $('.the-date')[0].dataset.date
    const urlPath = document.location.pathname
    $.get(urlPath + '/update/' + date)
      .done(function (htmlParts) {
        $('#per-night-menu').replaceWith(htmlParts.per_day)
        $('.channel-day-data').html(htmlParts.table)
        meta = parseJsonFromDOM('#table-metadata')
        if (Object.keys(meta).length !== 0) {
          applySelected(meta, selected)
          createTableControlUI(meta, $('#table-controls'), selected)
        }
      })
      .fail(function () {
        console.log("Couldn't reach server")
      })
  }, 5000)
})(jQuery)
