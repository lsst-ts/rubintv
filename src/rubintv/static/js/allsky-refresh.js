(function($){
  let url_path = document.location.pathname;
  let currentImage = $('.current-still');
  let currentMovie = $('.current-movie')

  setInterval(function refresh(){
    $.get(url_path + "/update/image", function(data){
      if (data.channel == "image"){
        currentImage.find('img').attr({'src': data.url})
        currentImage.find('.subheader h3').text(`${data.date} : Sequence ${data.seq}`);
        currentImage.find('.desc').text(data.name)
      }
    });
  }, 5000);

  let videoCheckLatest = function() {
    video = currentMovie.find("video")[0];
    $.get(url_path + "/update/monitor", function(data){
    let currentMovieUrl = $(video).find('source').attr('src');
    if (data.channel == "monitor" && data.url != currentMovieUrl) {
      $(video).find('source').attr({'src': data.url});
      currentMovie.find('.subheader h3').text(`${data.date} ${data.seq}`);
      currentMovie.find('.desc').text(data.name);
      video.load();
      }
    });
  }

  setInterval(videoCheckLatest, 5000);

})(jQuery)
