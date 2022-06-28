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
  applySelected(defaultSelected, true);
  let selected = defaultSelected;

  // click to retrieve & display data for day:
  $('.day').click(function(){
    let date = this.dataset.date;
    let url_path = document.location.pathname;
    $('.channel-day-data').load(url_path + "/" + date, function(){
      applySelected(selected, true);
      createTableControlUI($('.channel-grid-heading'), selected);
    });

  });

  $('.year-title').click(function(){
    $year_to_open = $(this).parent('.year');
    if ($year_to_open.hasClass('open')) return;
    $('.year.open').removeClass('open').addClass('closed')
    $year_to_open.removeClass('closed').addClass('open');
  });


})(jQuery)
