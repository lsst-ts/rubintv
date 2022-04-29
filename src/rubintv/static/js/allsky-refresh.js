(function($){
  setInterval(function refreshImage(){
    let url_path = document.location.pathname;
    $('.current-still').load(url_path + "/update/image")
  }, 5000);

  setInterval(function refreshMovie(){
    let url_path = document.location.pathname;
    $('.current-movie').load(url_path + "/update/monitor")
  }, 1000 * 3600);

})(jQuery)
