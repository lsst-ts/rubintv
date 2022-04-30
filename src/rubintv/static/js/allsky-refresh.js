(function($){
  // setInterval(function refreshImage(){
  //   let url_path = document.location.pathname;
  //   $('.current-still').load(url_path + "/update/image")
  // }, 5000);

  setInterval(function refresh(){
    let url_path = document.location.pathname;

    $.get(url_path + "/update/monitor", function(data){
      let currentMovie = $('.current-movie')
      let currentMovieUrl = currentMovie.find('video source').attr('src');

      if (data.eventType == "monitor" && data.src != currentMovieUrl) {
        currentMovie.find('video source').attr({'src': data.src});
        currentMovie.find('.subheader h3').text(`${data.date} ${data.seq}`);
        currentMovie.find('.desc').text(data.name);
        currentMovie.find('video')[0].load();
        console.log('new movie found');
      } else {
        console.log('same movie');
      }
    });

    $.get(url_path + "/update/image", function(data){
      if (data.eventType == "image"){
        let currentImage = $('.current-still');
        currentImage.find('img').attr({'src': data.src})
        currentImage.find('.subheader h3').text(`${data.date} : Sequence ${data.seq}`);
        currentImage.find('.desc').text(data.name)
      }
    });
  }, 5000);


})(jQuery)
