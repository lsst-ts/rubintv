import { createTableControlUI, applySelected } from "./modules/table-control.js";

(function($){

  let defaultSelected = [
    "exposure_time",
    "filter",
    "disperser",
    "airmass",
    "target_name",
    "time_begin_tai",
  ];

  createTableControlUI($('.channel-grid-heading'), defaultSelected);
  applySelected(defaultSelected);
  let selected = defaultSelected;

  setInterval(function refreshTable(){
    let date = $('.the-date')[0].dataset.date;
    let url_path = document.location.pathname;
    $('.channel-day-data').load(url_path + "/update/" + date, function() {
      applySelected(selected);
      createTableControlUI($('.channel-grid-heading'), selected);
    });
  }, 5000);

})(jQuery)
