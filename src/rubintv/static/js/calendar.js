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

     $.get(url_path + "/" + date, function(res){
      $('.channel-day-data').html(res);
    }).done(function(){
      applySelected(selected, true);
      createTableControlUI($('.channel-grid-heading'), selected);
    }).fail(function(){
      console.log("Couldn't reach server");
    });

  });

  $('.year-title').click(function(){
    let $year_to_open = $(this).parent('.year');
    if ($year_to_open.hasClass('open')) return;
    $('.year.open').removeClass('open').addClass('closed')
    $year_to_open.removeClass('closed').addClass('open');
  });


})(jQuery)
