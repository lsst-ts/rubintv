(function($){
  let url_path = document.location.pathname;

  setInterval(function refresh(){
    $.get(url_path + "/update/image", function(data){
      if (data.channel == "image"){
        let currentImage = $('.current-still');
        currentImage.find('img').attr({'src': data.src})
        currentImage.find('.subheader h3').text(`${data.date} : Sequence ${data.seq}`);
        currentImage.find('.desc').text(data.name)
      }
    });
  }, 5000);

  let onEnded = function() {
    const video = this;
    $.get(url_path + "/update/monitor", function(data){
    let currentMovie = $('.current-movie')
    let currentMovieUrl = $(video).find('source').attr('src');
    if (data.channel == "monitor" && data.src != currentMovieUrl) {
      $(video).find('source').attr({'src': data.src});
      currentMovie.find('.subheader h3').text(`${data.date} ${data.seq}`);
      currentMovie.find('.desc').text(data.name);
      video.load();
      } else {
        video.play()
      }
    });
  }

  $("video").on("ended", onEnded);

})(jQuery)
