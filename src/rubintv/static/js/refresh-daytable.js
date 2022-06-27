(function($){
  let metaText = document.querySelector("#table-metadata").text;
  let metaData = JSON.parse(metaText);

  const nameMappings = {
    "exposure_time": "Exp time",
    "target_name": "Target",
    "filter": "Filter",
    "disperser": "Disperser",
    "time_begin_tai": "TAI",
  }

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

  let defaultSelected = [
    "exposure_time",
    "filter",
    "disperser",
    "airmass",
    "target_name",
    "time_begin_tai",
  ];

  createTableControlUI();
  applySelected(defaultSelected);

  $(".table-control [type='checkbox']").change(function(e) {
   if (selected.includes(this.name)){
    selected.splice(selected.indexOf(this.name), 1);
    $('table .' + this.name).remove()
   } else {
    selected.push(this.name);
    applySelected([this.name]);
   }
  })

  let selected = defaultSelected;

  function applySelected(selected) {
    selected.forEach(attribute => {
      let last_header_cell = $('.grid-title').last();
      let el = $("<th>",{class: "grid-title sideways " + attribute});
      let name = checkbox_mapping[attribute] ? checkbox_mapping[attribute] : attribute;
      el.text(name);
      last_header_cell.after(el);
    });

    Object.entries(metaData).forEach(([seq, attributes]) => {
      let seq_row = $(`#seqno-${seq}`);

      selected.forEach(attribute => {
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

  function createTableControlUI(){
    let panel = $("<div>", {class: "table-panel"});
    panel.append($("<h3>", {class: "table-control-title", text: "Add/Remove Columns"}));
    let controls = $("<div>", {class: "table-controls"});
    // get the first row of data for list of all available attrs
    let attrs = metaData[Object.keys(metaData)[0]];
    Object.keys(attrs).forEach(attr => {
      let title = checkbox_mapping[attr] ? checkbox_mapping[attr] : attr
      let label = $("<label>",{for: attr}).text(title);
      let checkBox = $("<input>", {type: "checkbox", name: attr, value: 1});
      if (defaultSelected.includes(attr)) {
        checkBox.attr('checked', true);
      }
      let control = $("<div>",{class: "table-control"});
      control.append(checkBox);
      control.append(label);
      controls.append(control);
    });
    panel.append(controls);
    $('.sidebar').append(panel);
  }

  // setInterval(function refreshTable(){
  //   let date = $('.the-date')[0].dataset.date;
  //   let url_path = document.location.pathname;
  //   $('.channel-day-data').load(url_path + "/update/" + date, function() {
  //     applySelected(selected);
  //   });
  // }, 5000);

})(jQuery)
