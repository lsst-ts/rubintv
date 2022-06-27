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

let metaText = document.querySelector("#table-metadata").text;
let metaData = JSON.parse(metaText);
let controlsOpen = false;

export function applySelected(selection) {
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
}

export function createTableControlUI($elementToAppendTo, selection){
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
     applySelected([this.name]);
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
