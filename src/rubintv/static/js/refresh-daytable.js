(function($){
  setInterval(function refreshTable(){
    let date = $('.the-date')[0].dataset.date;
    let url_path = document.location.pathname;
    $('.channel-day-data').load(url_path + "/update/" + date)
  }, 5000);
})(jQuery)
