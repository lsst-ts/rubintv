(function($){
  // click to retrieve & display data for day:
  $('.day').click(function(){
    let date = this.dataset.date;
    let url_path = document.location.pathname;
    $('.channel-day-data').load(url_path + "/" + date);
  });
})(jQuery)
