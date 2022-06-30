const checkbox_mapping = {
  'id': 'Exposure id',
  'exposure_time': 'Exposure time',
  'dark_time': 'Darktime',
  'observation_type': 'Image type',
  'observation_reason': 'Observation reason',
  'day_obs': 'dayObs',
  'seq_num': 'seqNum',
  'group_id': 'Group id',
  'target_name': 'Target',
  'science_program': 'Science program',
  'tracking_ra': 'RA',
  'tracking_dec': 'Dec.',
  'sky_angle': 'Sky angle',
  'azimuth': 'Azimuth',
  'zenith_angle': 'Zenith angle',
  'time_begin_tai': 'TAI',
  'filter': 'Filter',
  'disperser': 'Disperser',
  'airmass': 'Airmass',
};

export function loadMetadata(){
  let metaText = document.querySelector("#table-metadata").text;
  return JSON.parse(metaText);
}

let controlsOpen = false;

export function applySelected(metaData, selection, sortable = false) {
   // empty object test- there's no data, just go home
   if (Object.keys(metaData).length == 0) return;

  selection.forEach(attribute => {
    let last_header_cell = $('.grid-title').last();
    let el = $("<th>",{class: "grid-title sideways " + attribute});
    let name = checkbox_mapping[attribute] ? checkbox_mapping[attribute] : attribute;
    el.text(name);
    last_header_cell.after(el);
  });

  Object.entries(metaData).forEach(([seq, attributes]) => {
    let seq_row = $(`#seqno-${seq}`);

    selection.forEach(attribute => {
      let seq_row_last_cell = seq_row.find('td').last();
      let el = $("<td>",{class: "meta grid-cell " + attribute});
      let val = attributes[attribute];
      if (typeof val === "number") {
        val = (+val.toFixed(3));
      }
      el.text(val);
      seq_row_last_cell.after(el);
    });
  });
  if (sortable) {
    makeTableSortable();
  }
}

export function createTableControlUI(metaData, $elementToAppendTo, selection){
  // empty object test- there's no data, just go home
  if (Object.getOwnPropertyNames(metaData).length == 0) return;

  let panel = $("<div>", {class: "table-panel"});
  panel.append($("<button>", {class: "table-control-button", text: "Add/Remove Columns"}));
  let controls = $("<div>", {class: "table-controls"});
  // get the first row of data for list of all available attrs

  let attrs = metaData[Object.keys(metaData)[0]];
  Object.keys(attrs).forEach(attr => {
    let title = checkbox_mapping[attr] ? checkbox_mapping[attr] : attr
    let label = $("<label>",{for: attr}).text(title);
    let checkBox = $("<input>", {type: "checkbox", name: attr, value: 1});
    if (selection.includes(attr)) {
      checkBox.attr('checked', true);
    }
    let control = $("<div>",{class: "table-control"});
    control.append(checkBox);
    control.append(label);
    controls.append(control);
  });
  panel.append(controls);
  $elementToAppendTo.append(panel);

  if (controlsOpen) {
    $(".table-panel").addClass('open');
  }

  $(".table-control [type='checkbox']").change(function(e) {
    if (selection.includes(this.name)){
     selection.splice(selection.indexOf(this.name), 1);
     $('table .' + this.name).remove()
    } else {
     selection.push(this.name);
     applySelected(metaData, [this.name]);
    }
   });

   $(".table-control-button").click(function(){
    $(".table-panel").toggleClass('open');
    if (controlsOpen) {
      controlsOpen = false;
    } else {
      controlsOpen = true;
    }
   });
}

function makeTableSortable() {
  document.querySelectorAll('th').forEach(th_elem => {
    let asc=true
    const index = Array.from(th_elem.parentNode.children).indexOf(th_elem)
    th_elem.addEventListener('click', (e) => {
        const arr = [... th_elem.closest("table").querySelectorAll('tbody tr')]
        arr.sort( (a, b) => {
            let a_val = a.children[index].innerText;
            let b_val = b.children[index].innerText;
            if (!isNaN(a_val) && !isNaN(b_val)){
              a_val = +a_val;
              b_val = +b_val;
              return (asc) ? a_val > b_val : a_val < b_val;
            }
            return (asc) ? a_val.localeCompare(b_val) : b_val.localeCompare(a_val);
        })
        arr.forEach(elem => {
            th_elem.closest("table").querySelector("tbody").appendChild(elem)
        })
        asc = !asc
    });
  });
}
