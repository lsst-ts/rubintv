import {
  _getById, _elWithAttrs, _elWithClass
}
  from './utils.js'

export class TableControls {
  constructor (defaultAttrs, metaData, elementToAppendTo, drawToTableCallback) {
    this.camera = document.querySelector('body').className
    this.defaultAttrs = defaultAttrs
    this.updateMetadata(metaData)
    const saved = this.retrieveSelected()
    this.selected = saved || defaultAttrs
    this.elementToAppendTo = elementToAppendTo
    this.drawToTableCallback = drawToTableCallback

    this.controlsOpen = false
    this.toggleAll = false
    this.draw()
  }

  orderSelected () {
    const fromTheDefaults = this.defaultAttrs.filter(attr => this.selected.includes(attr))
    const notInDefaults = this.selected.filter(attr => !this.defaultAttrs.includes(attr))
    this.selected = fromTheDefaults.concat(notInDefaults)
  }

  union (arrayA, arrayB) {
    return Array.from(new Set(arrayA.concat(arrayB)))
  }

  retrieveSelected () {
    const retrieved = localStorage[this.camera]
    return (retrieved && JSON.parse(retrieved))
  }

  storeSelected (selected) {
    localStorage[this.camera] = JSON.stringify(selected)
  }

  updateMetadata (metaData) {
    this.metaData = metaData
    this.attributes = this.getAttributesFrom(metaData)
  }

  getAttributesFrom (metaData) {
    // get the set of all data for list of all available attrs
    const allAttrs = Object.values(metaData).map(obj => Object.keys(obj)).flat()
    const attrsWithIndicators = new Set(this.defaultAttrs.concat(allAttrs))
    // filter out the indicators (first char is '_')
    return Array.from(attrsWithIndicators).filter(el => el[0] !== '_')
  }

  draw () {
    const panel = _elWithClass('div', 'table-panel')
    const controls = _elWithClass('div', 'table-controls')
    const button = _elWithAttrs('button', { class: 'table-control-button', text: 'Add/Remove Columns' })
    panel.appendChild(button)

    this.attributes.forEach(title => {
      const label = _elWithAttrs('label', { for: title, text: title })
      const checkBox = _elWithAttrs('input', { type: 'checkbox', id: title, name: title, value: 1 })

      if (this.selected.includes(title)) {
        checkBox.setAttribute('checked', true)
      }

      const control = _elWithClass('div', 'table-control')
      label.prepend(checkBox)
      control.append(label)
      controls.append(control)
    })

    panel.append(controls)
    document.querySelector(this.elementToAppendTo).append(panel)

    if (this.controlsOpen) {
      panel.classList.add('open')
    }

    const checkBoxes = document.querySelectorAll(".table-control [type='checkbox']")
    Array.from(checkBoxes).forEach(cb => {
      cb.addEventListener('change', this.handleCheckboxChange.bind(this))
    })

    document.querySelector('.table-control-button')
      .addEventListener('click', () => {
        if (this.controlsOpen) {
          panel.classList.remove('open')
          this.controlsOpen = false
        } else {
          panel.classList.add('open')
          this.controlsOpen = true
        }
      })

    this.drawJumpButtonControls(self.elementToAppendTo)
    this.addDownloadMetadataButton()
  }

  handleCheckboxChange (e) {
    const thisEl = e.target
    if (this.selected.includes(thisEl.name)) {
      this.selected.splice(this.selected.indexOf(thisEl.name), 1)
    } else {
      this.selected.push(thisEl.name)
    }
    this.orderSelected()
    this.drawToTableCallback(this.metaData, this.selected)
    this.storeSelected(this.selected)
  }

  drawJumpButtonControls () {
    const icon = _elWithAttrs('img', { src: '/rubintv/static/images/to-top.svg' })
    const toTop = _elWithAttrs('button', { class: 'to-top jump-button', title: 'To top' })
    toTop.append(icon)
    const toBottom = _elWithAttrs('button', { class: 'to-bottom jump-button', title: 'To bottom' })
    toBottom.append(icon.cloneNode(true))

    const buttonsPlace = document.querySelector('.jump-buttons')
    buttonsPlace.append(toTop)
    buttonsPlace.append(toBottom)

    toTop.addEventListener('click', () => {
      _getById('channel-day-data').scrollIntoView()
    })

    toBottom.addEventListener('click', () => {
      _getById('channel-day-data').scrollIntoView(false)
    })
  }

  addDownloadMetadataButton () {
    const button = _elWithAttrs('button', { class: 'button button-small download-metadata', text: 'Download Metadata' })
    _getById('table-controls').after(button)

    const camera = document.body.className
    const date = _getById('the-date').dataset.date
    button.addEventListener('click', () => {
      const a = document.createElement('a')
      const blob = new Blob([JSON.stringify(this.metaData)])
      const url = window.URL.createObjectURL(blob)
      a.href = url
      a.download = `${camera}_${date}.json`
      a.click()
      URL.revokeObjectURL(blob)
    })
  }
}
