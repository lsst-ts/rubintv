from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Dict

import yaml

from .models import Camera, Channel, Location


class ModelsInitator:
    """Oversee the loading and initialising of the various models used by the
    app."""

    def __init__(self) -> None:
        models_file_path = Path(__file__).parent / "models_data.yml"
        with open(models_file_path, "r") as file:
            data = yaml.safe_load(file)
        self._cameras = self._get_cameras(data)
        self._locations = self._get_locations(data)
        self._services = self._get_services(data)
        self._metadata_headings_to_cameras(data)

    @property
    def cameras(self) -> Dict[str, Camera]:
        """Return a dictionary of `Camera` objects.
        (`Dict` [`str`, `Camera`], read-only)"""
        return self._cameras

    @property
    def locations(self) -> Dict[str, Location]:
        """Return a dictionary of `Location` objects.
        (`Dict` [`str`, `Location`], read-only)"""
        return self._locations

    @property
    def services(self) -> Dict[str, Dict[str, str] | Dict[str, Channel]]:
        """Return a dictionary of services.
        (`Dict` [`str`, `Dict` [`str`, `str`] | `Dict` [`str`, `Channel`]],
        read-only)

        See Also
        --------
        _get_services()
        """
        return self._services

    def _get_cameras(self, data: Dict) -> Dict[str, Camera]:
        """Return a dictionary of `Camera` objects from the given yaml file data
        dictionary.

        `Camera` objects include a dictionary of associated `Channel` objects.

        Parameters
        ----------
        data : `Dict`
            Contents of the models yaml file as a dict.

        Returns
        -------
        cameras : `Dict` [`str`, `Camera`]`
            Dictionary of Camera objects keyed by name.
        """
        cameras = {}
        d_cameras = data["Cameras"]
        for cam_name, cam_dict in d_cameras.items():
            # makes Camera objects from dictionaries
            cam = dataclass_from_dict(Camera, cam_dict)
            cam.slug = cam_name

            # make dict of camera's channels into channel objects
            chans = self._channel_dict_to_channel_objs(cam.channels)
            cam.channels = chans
            # do the same for the per day channels
            per_day_chans = self._channel_dict_to_channel_objs(
                cam.per_day_channels
            )
            cam.per_day_channels = per_day_chans

            cameras[cam_name] = cam
        return cameras

    def _channel_dict_to_channel_objs(
        self, channels_dict: Dict
    ) -> Dict[str, Channel]:
        """Returns a dict of Channel objects keyed by name from a dict of channel.
        parameters

        Parameters
        ----------
        channels_dict : `Dict`
            A dict of channel parameters as given in the model data yaml file.

        Returns
        -------
        channels : `Dict` [`str`, `Channel`]
            A dict of Channels keyed by name.
        """
        channels = {}
        for chan_name, chan_dict in channels_dict.items():
            channel = dataclass_from_dict(Channel, chan_dict)
            # insert lowercase Channel name as 'slug'
            channel.slug = chan_name
            channels[chan_name] = channel
        return channels

    def _get_locations(self, data: Dict) -> Dict[str, Location]:
        """Returns a dictionary of Location objects from the given yaml file data
        dictionary.

        Location objects include a dictionary of associated Cameras and Services.

        Parameters
        ----------
        data : `Dict`
            The contents of the models yaml file as a dict.

        Returns
        -------
        locations: `Dict`[`str`, `Location`]
            A dictionary of Location objects keyed by name.
        """
        locations = {}
        d_locations = data["Locations"]
        for loc_name, loc in d_locations.items():
            location = dataclass_from_dict(Location, loc)
            location.slug = loc_name
            locations[loc_name] = location
        return locations

    def _get_services(
        self, data: Dict
    ) -> Dict[str, Dict[str, str] | Dict[str, Channel]]:
        """Returns a dictionary of services from the given yaml file data
        dictionary.

        Parameters
        ----------
        data : `Dict`
            The contents of the models yaml file as a dict.

        Returns
        -------
        services : `Dict` [`str`, `Dict` [`str`, `str`] | `Dict` [`str`, `Channel`]]
            Services dict with keys:
                ``"display_name"``
                Title to display for `Camera` or other group of services (`str`).
                ``"channels"``
                Dict of `Camera` channels (`Dict` [`str`, `str`]).
                ``"services"``
                Dict of services (`Dict` [`str`, `str`]).
                The dict describes a heartbeat file and it's display name.

                -   The key is a partial prefix used for finding the heartbeat file
                    in the bucket.
        """
        services: Dict[str, Dict] = data["Services"]
        for s in services:
            if "channels" in services[s]:
                # expand name of camera out into camera's channels
                cam = services[s]["channels"]
                chans: Dict[str, Channel] = self._cameras[cam].channels
                services[s]["channels"] = chans
        return services

    def _metadata_headings_to_cameras(self, data: Dict) -> None:
        """Insert metadata column headings into `Camera`s.

        Parameters
        ----------
        data : `Dict`
        """
        headings: Dict = data["MetadataHeadings"]
        for cam in headings:
            if cam in self.cameras:
                cam_headings = headings[cam]
                self._cameras[cam].metadata_headers = cam_headings
        return


def dataclass_from_dict(cls: Any, data: Dict) -> Any:
    """Make a dataclass from a dict

    Parameters
    ----------
    cls : `Any`
        The target dataclass
    data : `Dict`
        The given dict

    Returns
    -------
    cls : `Any`
    """
    return cls(
        **{
            key: (
                data[key]
                if val.default == val.empty
                else data.get(key, val.default)
            )
            for key, val in inspect.signature(cls).parameters.items()
        }
    )
