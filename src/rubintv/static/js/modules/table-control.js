/* global $ */

const checkboxMapping = {
  id: 'Exposure id',
  exposure_time: 'Exposure time',
  dark_time: 'Darktime',
  observation_type: 'Image type',
  observation_reason: 'Observation reason',
  day_obs: 'dayObs',
  seq_num: 'seqNum',
  group_id: 'Group id',
  target_name: 'Target',
  science_program: 'Science program',
  tracking_ra: 'RA',
  tracking_dec: 'Dec.',
  sky_angle: 'Sky angle',
  azimuth: 'Azimuth',
  zenith_angle: 'Zenith angle',
  time_begin_tai: 'TAI',
  filter: 'Filter',
  disperser: 'Disperser',
  airmass: 'Airmass',
  focus_z: 'Focus-Z',
  Seeing: 'DIMM Seeing'
}

export function loadMetadata () {
  const metaText = document.querySelector('#table-metadata').text
  return JSON.parse(metaText)
}

let controlsOpen = false

export function applySelected (metaData, selection, sortable = false) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return

  selection.forEach(attribute => {
    const lastHeaderCall = $('.grid-title').last()
    const el = $('<th>', { class: 'grid-title sideways ' + attribute })
    const name = checkboxMapping[attribute] ? checkboxMapping[attribute] : attribute
    el.text(name)
    lastHeaderCall.after(el)
  })

  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = $(`#seqno-${seq}`)

    selection.forEach(attribute => {
      const seqRowLastCell = seqRow.find('td').last()
      const el = $('<td>', { class: 'meta grid-cell ' + attribute })
      let val = attributes[attribute]
      if (typeof val === 'number') {
        val = (+val.toFixed(3))
      }
      el.text(val)
      seqRowLastCell.after(el)
    })
  })
  if (sortable) {
    makeTableSortable()
  }
}

export function createTableControlUI (metaData, $elementToAppendTo, selection) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length !== 0) {
    const panel = $('<div>', { class: 'table-panel' })
    panel.append($('<button>', { class: 'table-control-button', text: 'Add/Remove Columns' }))
    const controls = $('<div>', { class: 'table-controls' })
    // get the first row of data for list of all available attrs

    const attrs = metaData[Object.keys(metaData)[0]]
    Object.keys(attrs).forEach(attr => {
      const title = checkboxMapping[attr] ? checkboxMapping[attr] : attr
      const label = $('<label>', { for: attr }).text(title)
      const checkBox = $('<input>', { type: 'checkbox', id: attr, name: attr, value: 1 })
      if (selection.includes(attr)) {
        checkBox.attr('checked', true)
      }
      const control = $('<div>', { class: 'table-control' })
      label.prepend(checkBox)
      control.append(label)
      controls.append(control)
    })
    panel.append(controls)
    $elementToAppendTo.append(panel)

    if (controlsOpen) {
      $('.table-panel').addClass('open')
    }

    $(".table-control [type='checkbox']").change(function (e) {
      if (selection.includes(this.name)) {
        selection.splice(selection.indexOf(this.name), 1)
        $('table .' + this.name).remove()
      } else {
        selection.push(this.name)
        applySelected(metaData, [this.name])
      }
    })

    $('.table-control-button').click(function () {
      $('.table-panel').toggleClass('open')
      if (controlsOpen) {
        controlsOpen = false
      } else {
        controlsOpen = true
      }
    })
  }

  addToTopBottomControls($elementToAppendTo)
}

function makeTableSortable () {
  document.querySelectorAll('th').forEach(thElem => {
    let asc = true
    const index = Array.from(thElem.parentNode.children).indexOf(thElem)
    thElem.addEventListener('click', (e) => {
      const arr = [...thElem.closest('table').querySelectorAll('tbody tr')]
      arr.sort((a, b) => {
        let aVal = a.children[index].innerText
        let bVal = b.children[index].innerText
        if (!isNaN(aVal) && !isNaN(bVal)) {
          aVal = +aVal
          bVal = +bVal
          return (asc) ? aVal > bVal : aVal < bVal
        }
        return (asc) ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      })
      arr.forEach(elem => {
        thElem.closest('table').querySelector('tbody').appendChild(elem)
      })
      asc = !asc
    })
  })
}

function addToTopBottomControls () {
  const icon = $('<img>', { src: '/rubintv/static/images/to-top.svg' })
  const toTop = $('<button>', { class: 'to-top jump-button', title: 'To top' }).append(icon)
  const toBottom = $('<button>', { class: 'to-bottom jump-button', title: 'To bottom' }).append(icon.clone())
  toTop.click(function () {
    const tableHeight = $('#table-top').offset().top
    $(window).scrollTop(tableHeight)
  })
  toBottom.click(function () {
    const tableHeight = $('table').offset().top + $('table').height()
    $(window).scrollTop(tableHeight)
  })
  $('.jump-buttons').append(toTop).append(toBottom)
}
