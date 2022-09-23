/* global $ */

function historicalReset () {
  const $form = $('#historicalReset')
  $form.click(function (e) {
    e.preventDefault()
    $(this).find('.pending').toggleClass('hidden')
    $.post('reload_historical', function (jsonRes) {
      $(this).find('.pending').toggleClass('hidden')
      $form.replaceWith(
        $('<div>', { class: 'message success' }).text('Historical Data Reloaded Successfully')
          .append(
            $('<pre>').text(JSON.stringify(jsonRes, null, '\t'))
          )
      )
    })
  })
}

historicalReset()
