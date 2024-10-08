import PropTypes from 'prop-types'

// TODO: Convert these defs to use typescript instead.
// See: DM-46475 (https://rubinobs.atlassian.net/browse/DM-46475)

/** A single item of metadata is either a string, number or nested object of
 * key-value pairs. In the case of the latter, if one of the keys is
 * 'DISPLAY_VALUE', it's value is a UTF-8 encoded character to display as an
 * icon in a button in the table */
export const metadatumType = PropTypes.oneOfType(
  [PropTypes.number, PropTypes.string, PropTypes.object]
)

/** metadata is in key-value pairs */
export const metadataType = PropTypes.objectOf(metadatumType)

/** An event takes the shape:
 * {
    key: <reference for object in S3 bucket>
    hash: <hash of object given by S3>
    camera_name: <name of associated camera>
    day_obs: <date of event in format 'YYYY-MM-DD'>
    channel_name: <name of associated channel>
    seq_num: <sequence number of event>
    filename: <filename of the event>
    ext: <file extension>
  } */
export const eventType = PropTypes.shape({
  key: PropTypes.string,
  hash: PropTypes.string,
  camera_name: PropTypes.string,
  day_obs: PropTypes.string,
  channel_name: PropTypes.string,
  seq_num: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  filename: PropTypes.string,
  ext: PropTypes.string
})

/** A camera takes the shape:
 * {
    name: <name of the camera>
    title: <camera display title>
    online: <true for online i.e. will display web page>
    metadata_from: <n/a>
    logo: <filename of logo>
    channels: <array of channel objects>
    night_report_label: <display name for Night Report>
    metadata_cols: <names and optional description of default columns>
    image_viewer_link: <template for hi-res image viewer link>
    copy_row_template: <template for copy to clipboard text>
  * } */
export const cameraType = PropTypes.shape({
  name: PropTypes.string,
  title: PropTypes.string,
  online: PropTypes.bool,
  metadata_from: PropTypes.string,
  logo: PropTypes.string,
  channels: PropTypes.arrayOf(PropTypes.object),
  night_report_label: PropTypes.string,
  metadata_cols: PropTypes.object,
  image_viewer_link: PropTypes.string,
  copy_row_template: PropTypes.string
})

/** channel data is formatted for ease of laying out in a table. It's keyed
 * by seq. num
 */
export const channelDataType = PropTypes.objectOf(
  PropTypes.objectOf(eventType)
)

export const nightReportData = PropTypes.shape({
  /**
   * nightReportData takes the shape:
   
    key: <reference for object in S3 bucket>
    hash: <hash of object given by S3>
    camera: <name of associated camera>
    day_obs: <date of event in format 'YYYY-MM-DD'>
    group: <group name of plot>
    filename: <filename of the event>
    ext: <file extension>
   */
  key: PropTypes.string,
  hash: PropTypes.string,
  camera: PropTypes.string,
  day_obs: PropTypes.string,
  group: PropTypes.string,
  filename: PropTypes.string,
  ext: PropTypes.string
})

export const mosaicSingleView = PropTypes.shape({
  channel: PropTypes.string,
  metaColumns: PropTypes.arrayOf(PropTypes.string),
  latestImage: PropTypes.string,
  latestMetadata: metadataType,
})
