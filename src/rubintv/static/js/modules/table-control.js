import {
  _getById, _elWithAttrs, _elWithClass,
  removeColumnFromTableFor
}
  from './utils.js'

export class TableControls {
  constructor (defaultAttrs, metaData, elementToAppendTo, drawToTableCallback) {
    this.defaultAttrs = defaultAttrs
    this.metaData = metaData
    this.attributes = this.getAttributesFrom(metaData)
    this.selected = this.retrieveSelected() || defaultAttrs
    this.elementToAppendTo = elementToAppendTo
    this.drawToTableCallback = drawToTableCallback

    this.controlsOpen = false
    this.toggleAll = false
  }

  retrieveSelected () {
    const retrieved = localStorage.selected
    return (retrieved && JSON.parse(retrieved))
  }

  storeSelected (selected) {
    localStorage.selected = JSON.stringify(selected)
  }

  updateMetadata (metaData) {
    this.metaData = metaData
    this.attributes = this.getAttributesFrom(metaData)
  }

  getAttributesFrom (metaData) {
    // get the set of all data for list of all available attrs
    const allAttrs = Object.values(metaData).map(obj => Object.keys(obj)).flat()
    const attrsWithIndicators = new Set(allAttrs)
    // filter out the indicators
    return Array.from(attrsWithIndicators).filter(el => el[0] !== '_')
  }

  draw () {
    const panel = _elWithClass('div', 'table-panel')
    const controls = _elWithClass('div', 'table-controls')
    const button = _elWithAttrs('button', { class: 'table-control-button', text: 'Add/Remove Columns' })
    panel.appendChild(button)

    const toggleAllLabel = _elWithAttrs('label', { for: 'toggle-all', text: 'Toggle all' })
    const toggleAllBox = _elWithAttrs('input', { type: 'checkbox', id: 'toggle-all', name: 'toggle-all', value: 1 })
    if (this.toggleAll) { toggleAllBox.checked = true }
    const control = _elWithClass('div', 'table-control toggle')
    toggleAllLabel.prepend(toggleAllBox)
    control.append(toggleAllLabel)
    controls.prepend(control)

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
    if (thisEl.name === 'toggle-all') {
      this.handleToggleAllChange(thisEl)
    } else {
      if (this.selected.includes(thisEl.name)) {
        this.selected.splice(this.selected.indexOf(thisEl.name), 1)
        removeColumnFromTableFor(thisEl.name)
      } else {
        this.selected.push(thisEl.name)
        this.drawToTableCallback(this.metaData, [thisEl.name])
      }
    }
    this.storeSelected(this.selected)
  }

  handleToggleAllChange (toggleBox) {
    if (toggleBox.checked) {
      const notYetSelected = []
      // find those not selected yet
      this.attributes.forEach((attr) => {
        !this.selected.includes(attr) && notYetSelected.push(attr)
      })
      // add them to the table
      this.drawToTableCallback(this.metaData, notYetSelected)
      // check their boxes
      notYetSelected.forEach(attr => {
        _getById(attr).checked = true
      })
      // add them to 'selected'
      this.selected = this.selected.concat(notYetSelected)
      this.toggleAll = true
    } else {
      // makes sure _all_ metadata attributes are removed
      // some may be defined as default but not be in the metadata
      const allAttrs = Array.from(new Set(this.attributes.concat(this.defaultAttrs)))
      allAttrs.forEach(attr => {
        removeColumnFromTableFor(attr)
        // uncheck all boxes
        if (_getById(attr)) {
          _getById(attr).checked = false
        }
      })
      this.selected = this.defaultAttrs
      this.selected.forEach(attr => {
        if (_getById(attr)) {
          _getById(attr).checked = true
        }
      })
      this.drawToTableCallback(this.metaData, this.selected)
      this.toggleAll = false
    }
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
