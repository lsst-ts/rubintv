from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dateutil.tz import gettz

from rubintv.models.models_helpers import string_int_to_date


@dataclass
class Channel:
    """A container for a category of images from a `Camera`.

    Parameters
    ----------
    name : `str`
        Name of the channel.
    prefix : `str`
        Lookup prefix for the GCS Bucket.
    slug : `str`
        The part of the URL that identifies this channel in a web request.
        Simplified version of the name, lowercase with no white-space and only
        ``-`` or ``_`` seperators.
    label : `str`
        Optional extra string for GUI buttons. If not given, the label is set
        the same as the name.
    service_dependency : `str`
        Name of the production service on which the production generator of
        this channel depends. e.g. ``"auxtel_monitor"`` is dependent on
        ``"auxtel_isr_runner"``. Used as a url slug (see slug above).
    """

    name: str
    prefix: str
    slug: str = ""
    label: str = ""
    service_dependency: str = ""

    def __post_init__(self) -> None:
        if self.label == "":
            self.label = self.name


@dataclass
class Camera:
    """A container for a single camera

    Parameters
    ----------
    name : `str`
        Name of the camera/image producer.
    online : `bool`
        To display the camera or not.
    slug : `str`
        The part of the URL that identifies this camera in a web request.
        Simplified version of the name, lowercase with no white-space and only
        ``-`` or ``_`` seperators.
    metadata_slug: `str`
        Optional slug used for locating shared metadata files in the bucket.
        If none is given, the slug above is used.
    logo : `str`
        Name (including extension) of the image file to display in the GUI
        button. Images are looked for in ``"/static/images/logos/"``.
    has_image_viewer : `bool`
        If ``True`` a column is drawn in the table for this camera with a link
        generated to point to an external image viewer for each monitor event.
    channels : `dict` [`str`, `Channel`]
        `Channel`s belonging to this camera, keyed by name.
    per_day_channels : `dict` [`str`, `Channel`]
        `Channel`s belonging to this camera, keyed by name. Per day
        channels are for categories of event that only occur once per
        observation date e.g. a movie of the night's images.
    night_report_prefix : `str`
        Used to form part of the bucket lookup for night reports. If left unset
        the camera is considered not to produce night reports.
    metadata_headers : `dict` [`str`, `dict` [`str`, `str`]]] | `dict`[`str`,
    `str`]
        The default column headers for the metadata in the table for this
        `Camera`.
        -   If it's a simple `dict`, a key is a column name and a value is a
            description of the column.
        -   The more complex dict is keyed by group name and then as above.

    js_entry : `str`
        Used in the template to point to a javascript file that manages table
        updating and other dynamic interfaces.
    """

    name: str
    online: bool
    _slug: str = field(init=False, repr=False)
    metadata_slug: str = ""
    logo: str = ""
    has_image_viewer: bool = False
    channels: dict[str, Channel] = field(default_factory=dict)
    per_day_channels: dict[str, Channel] = field(default_factory=dict)
    night_report_prefix: str = ""
    metadata_headers: dict[str, dict[str, str]] | dict[str, str] = field(
        init=False
    )
    js_entry: str = ""

    @property
    def slug(self) -> str:
        return self._slug

    @slug.setter
    def slug(self, slug: str) -> None:
        self._slug = slug
        if not self.metadata_slug:
            self.metadata_slug = slug


@dataclass
class Location:
    """Describes a site grouping of cameras

    Parameters
    ----------
    name: `str`
        The name of the location.
    bucket: `str`
        The identifying name of the `Bucket` that stores this group's images and
        other files.
    services: `list` [`str`]
        The names of services to display on the admin status page as belonging
        to this location.
    slug: `str`
        The part of the URL that identifies this location in a web request.
        Simplified version of the name, lowercase with no white-space and only
        ``-`` or ``_`` seperators.
    logo: `str`
        Name (including extension) of the image file to display in the GUI
        button. Images are looked for in the path ``"/static/images/logos/"``.
    camera_groups: `dict` [`str`, `list` [`str`]]
        Used on the location's page. The dict key is used as the group title,
        and the list is of strings that are keys in a globally accessable dict
        of `Camera` objects (via
        ``web.Application["rubintv/models"]["cameras"]``)
    """

    name: str
    bucket: str
    services: list[str]
    slug: str = ""
    logo: str = ""
    camera_groups: dict[str, list[str]] = field(default_factory=dict)

    def all_cameras(self) -> list[str]:
        """Returns list of keys for the camera dict

        Returns
        -------
        list[str]
            _description_
        """
        all_cams: list[str] = []
        for cam_list in self.camera_groups.values():
            for cam in cam_list:
                all_cams.append(cam)
        return all_cams


@dataclass
class Event:
    """Wrapper for a single unit of GCS `Blob` metadata.

    The various fields are extrapolated from the Blob's public url which takes
    the form:

    ``f"{hostname}/{bucket_name}/{channel_prefix}/{channel-dashes-prefix}_dayObs_
    {date}_seqNum_{seq}.{ext}"``
    where:
        -   ``channel-dashes-prefix`` is ``channel_prefix`` with underscores
            converted to dashes
        -   ``date`` is as ``"YYYY-MM-DD"``
        -   ``seq`` is an unpadded integer
        -   ``ext`` is the file extension i.e. ``.png``

    Returns
    -------
    url: `str`
        The public url of the blob.
    name: `str`
        The last part of the url after the prefix.
    prefix: `str`
        The part of the url that identifies the channel the event belongs to.
    obs_date: `date`
        The date of the event.
    seq: `int`
        The sequence number of the event.
        In the case of All Sky, the sequence can be ``"final"`` which
        is converted to an integer.
    """

    url: str
    name: str = field(init=False)
    prefix: str = field(init=False)
    obs_date: date = field(init=False)
    seq: int = field(init=False)

    def parse_filename(self, delimiter: str = "_") -> tuple:
        """Split the filename into class attributes.

        Parameters
        ----------
        delimiter : str, optional
            The character that delimits the attributes, by default "_"

        Returns
        -------
        values : `tuple`
            A tuple of values used by `__post_init__` to fully init the object.
        """
        # Every bucket starts /rubintv
        regex = r"\/rubintv[_\w]+\/"
        cleaned_up_url = re.split(regex, self.url)[-1]
        prefix, name = cleaned_up_url.split(
            "/"
        )  # We know the name is the last part of the URL
        nList = name.split(delimiter)
        the_date = nList[2]
        year, month, day = map(int, the_date.split("-"))
        seq_str = nList[4][:-4]  # Strip extension
        if seq_str == "final":
            seq = 99999
        else:
            seq = int(seq_str)
        return (name, prefix, date(year, month, day), seq)

    def clean_date(self) -> str:
        return self.obs_date.strftime("%Y-%m-%d")

    def __post_init__(self) -> None:
        self.name, self.prefix, self.obs_date, self.seq = self.parse_filename()


@dataclass
class Night_Report_Event:
    """Wrapper for a night report blob.

        -   Night Reports can be located in a given bucket using the prefix:
            ``f"/{bucket}/{night_report_prefix}/"``.

        -   Filenames take the form:
            ``f"/{obs_date}/{group_name}/{measurement_name}.{file_ext}"``.

    Parameters
    ----------
    url: `str`
        The public url of the blob. This is used as the unique identifier of a
        plot image onsite.
    prefix: `str`
        The prefix used to locate the blob in the bucket. It's used as the
        delimeter by which to split the url into bucket hostname and the data
        stored in the filename.
    timestamp: `int`
        The timestamp of the blob. This is used to keep plot images up-to-date
        onsite.
    blobname: `str`
        The name by which to download the blob data from the bucket.
    group: `str`
        The name of the group the data belogs to.
    name: `str`
        The name of the plot or text item of data.
    _obs_date: `str`
        The observation date of the data.
    file_ext: `str`
        The file extension.
    """

    url: str
    prefix: str
    hash: str
    blobname: str = ""
    group: str = field(init=False)
    name: str = field(init=False)
    _obs_date: str = field(init=False)
    file_ext: str = field(init=False)

    @property
    def obs_date(self) -> date:
        return string_int_to_date(self._obs_date)

    def parse_filename(self) -> tuple:
        """Split the filename into parts.

        Returns
        -------
        `tuple`
             A tuple of values used by `__post_init__` to fully init the object.
        """
        parts = self.url.split(self.prefix + "/")[-1]
        # use spread in case of extended names
        d, group, *names = parts.split("/")
        obs_date = d
        raw_name, file_ext = "".join(names).split(".")
        name = "".join(raw_name).replace("_", " ")
        return (group, name, obs_date, file_ext)

    def __post_init__(self) -> None:
        (
            self.group,
            self.name,
            self._obs_date,
            self.file_ext,
        ) = self.parse_filename()

    def dict(self) -> dict:
        _dict = self.__dict__.copy()
        return _dict


def get_current_day_obs() -> date:
    """Get the current day_obs.

    The observatory rolls the date over at UTC minus 12 hours.

    Returns
    -------
    dayObs : `date`
        The current observation day.
    """
    utc = gettz("UTC")
    nowUtc = datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs
