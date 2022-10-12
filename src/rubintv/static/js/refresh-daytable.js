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
    $.get(urlPath + '/update/' + date, function (res) {
      $('.channel-day-data').html(res)
    }).done(function () {
      meta = parseJsonFromDOM('#table-metadata')
      applySelected(meta, selected)
      createTableControlUI(meta, $('#table-controls'), selected)
    }).fail(function () {
      console.log("Couldn't reach server")
    })
  }, 5000)
})(jQuery)
