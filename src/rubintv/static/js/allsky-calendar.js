(function($){
  // click to retrieve & display data for day:
  $('.day').click(function(){
    let date = this.dataset.date;
    let url_path = document.location.pathname;
    $('.current-movie').load(url_path + "/" + date);
  });
  $('.year-title').click(function(){
    $year_to_open = $(this).parent('.year');
    if ($year_to_open.hasClass('open')) return;
    $('.year.open').removeClass('open').addClass('closed')
    $year_to_open.removeClass('closed').addClass('open');
  });
})(jQuery)
