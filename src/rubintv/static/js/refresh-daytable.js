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

  let defaultSelected = [
    "exposure_time",
    "target_name",
    "filter",
    "disperser",
    "time_begin_tai"
  ];

  defaultSelected.forEach(element => {
    let last_header_cell = $('.grid-title').last();
    let el = $("<th>",{class: "grid-title sideways"});
    el.text(nameMappings[element]);
    last_header_cell.after(el);
  });

  Object.entries(metaData).forEach(([seq, value]) => {

    let seq_row = $(`#seqno-${seq}`);

    defaultSelected.forEach(element => {
      let seq_row_last_cell = seq_row.find('td').last();
      let el = $("<td>",{class: "meta grid-cell"});
      el.text(value[element]);
      seq_row_last_cell.after(el);
    });

  });
  // setInterval(function refreshTable(){
  //   let date = $('.the-date')[0].dataset.date;
  //   let url_path = document.location.pathname;
  //   $('.channel-day-data').load(url_path + "/update/" + date, function() {

  //   });
  // }, 5000);
})(jQuery)
