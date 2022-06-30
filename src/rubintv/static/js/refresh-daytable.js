import { createTableControlUI, applySelected, loadMetadata } from "./modules/table-control.js";

(function($){

  let defaultSelected = [
    "exposure_time",
    "observation_type",
    "target_name",
    "filter",
    "disperser",
    "airmass",
    "time_begin_tai",
  ];

  let meta = loadMetadata();
  createTableControlUI(meta, $('.channel-grid-heading'), defaultSelected);
  applySelected(meta, defaultSelected);
  let selected = defaultSelected;

  // setInterval(function refreshTable(){
  //   let date = $('.the-date')[0].dataset.date;
  //   let url_path = document.location.pathname;
  //   $.get(url_path + "/update/" + date, function(res){
  //     $('.channel-day-data').html(res);
  //   }).done(function(){
  //     meta = loadMetadata();
  //     applySelected(meta, selected);
  //     createTableControlUI(meta, $('.channel-grid-heading'), selected);
  //   }).fail(function(){
  //     console.log("Couldn't reach server");
  //   })
  // }, 5000);

})(jQuery)
