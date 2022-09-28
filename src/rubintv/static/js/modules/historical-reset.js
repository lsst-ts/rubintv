/* global $ */

function historicalReset () {
  const $form = $('#historicalReset')
  $form.click(function (e) {
    e.preventDefault()
    $form.find('.done').addClass('hidden')
    $form.find('.pending').toggleClass('hidden')
    $.post('reload_historical', function () {
      $form.find('.pending').toggleClass('hidden')
      $form.find('.done').toggleClass('hidden')
    })
  })
}

historicalReset()
