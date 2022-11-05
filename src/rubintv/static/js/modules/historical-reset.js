/* global $ */

function historicalReset () {
  const $form = $('#historicalReset')
  $form.click(function (e) {
    e.preventDefault()
    // hide 'done' in case button is pressed again
    $form.find('.done').addClass('hidden')
    $form.find('.pending').removeClass('hidden')
    const promise = $.post('reload_historical', function (data) {
      console.log(`${data}: reload success`)
    })
    promise.done(function () {
      $form.find('.pending').addClass('hidden')
      $form.find('.done').removeClass('hidden')
    })
  })
}

historicalReset()
