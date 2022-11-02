/* global $ */

const defaultSelected = [
  'Exposure time',
  'Image type',
  'Target',
  'Filter',
  'Disperser',
  'Airmass',
  'TAI',
  'DIMM Seeing'
]

export const DefaultSelected = defaultSelected

export function parseJsonFromDOM (element) {
  const metaText = document.querySelector(element).text
  return JSON.parse(metaText)
}

let controlsOpen = false

export function applySelected (metaData, selection, sortable = false) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length === 0) return

  selection.forEach(name => {
    const escapedName = _escapeName(name)
    const lastHeaderCall = $('.grid-title').last()
    const el = $('<th>', { class: 'grid-title sideways ' + escapedName })
    el.text(name)
    lastHeaderCall.after(el)
  })

  Object.entries(metaData).forEach(([seq, attributes]) => {
    const seqRow = $(`#seqno-${seq}`)

    selection.forEach(name => {
      const seqRowLastCell = seqRow.find('td').last()
      const el = $('<td>', { class: 'meta grid-cell ' + _escapeName(name) })
      let val = attributes[name]
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

function _escapeName (displayName) {
  return displayName.toLowerCase().replaceAll(' ', '_')
}

export function createTableControlUI (metaData, $elementToAppendTo, selection) {
  // empty object test- there's no data, just go home
  if (Object.keys(metaData).length !== 0) {
    const panel = $('<div>', { class: 'table-panel' })
    panel.append($('<button>', { class: 'table-control-button', text: 'Add/Remove Columns' }))
    const controls = $('<div>', { class: 'table-controls' })

    // get the set of all data for list of all available attrs
    const allAttrs = Object.values(metaData).map(obj => Object.keys(obj)).flat()
    const attrs = new Set(allAttrs)

    attrs.forEach(title => {
      const label = $('<label>', { for: title }).text(title)
      const checkBox = $('<input>', { type: 'checkbox', id: title, name: title, value: 1 })
      if (selection.includes(title)) {
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
        $('table .' + _escapeName(this.name)).remove()
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
