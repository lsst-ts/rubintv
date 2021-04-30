$(document).ready(function(){
      refreshDiv();
    });

    function refreshDiv(){
        $('#refresher').load(window.location.href + " #refresher" , function(){
           setTimeout(refreshDiv, 500);
        });
    }