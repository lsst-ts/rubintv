from itertools import chain
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic import BaseModel

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Heartbeat, Location

__all__ = ["ModelsInitiator", "dict_from_list_of_named_objects"]


class ModelsInitiator:
    """Loads and substantiates models with data from a yaml file.

    Instance variables
    ------------------
    self.locations : `List` [`Location`]
        The locations or sites where the cameras ar based.
    self.cameras : `List` [`Camera`]
        The cameras.
    self.heartbeats : `List` [`Heartbeat`]
        The heartbeats represent the health of background services.
    """

    def __init__(self) -> None:
        models_file_path = Path(__file__).parent / "models_data.yaml"
        with open(models_file_path, "r") as file:
            data = yaml.safe_load(file)
        cameras = self._populate_model(Camera, data["cameras"])
        self.cameras = self._attach_metadata_cols(
            cameras, data["metadata_cols"]
        )
        locations = self._populate_model(Location, data["locations"])
        self.locations = self._attach_cameras_to_locations(
            self.cameras, locations
        )
        heartbeats = self._populate_model(Heartbeat, data["heartbeats"])
        self.heartbeats = self._inject_heartbeat_channels(heartbeats)

    def _attach_cameras_to_locations(
        self, cameras: list[Camera], locations: list[Location]
    ) -> list[Location]:
        for location in locations:
            camera_groups = location.camera_groups.values()
            location_cams = chain(*camera_groups)
            for cam_name in location_cams:
                camera = find_first(cameras, "name", cam_name)
                if camera:
                    location.cameras.append(camera)
        return locations

    def _populate_model(
        self, cls: Type[BaseModel], data_dict: dict[str, list]
    ) -> list[Any]:
        """Generic method to convert data from the yaml file to lists of
        pydantic `BaseModel` backed classes.

        Parameters
        ----------
        cls : `Type` [`BaseModel`]
            The class to instantiate.
        data_dict : `dict` [`str`, `list`]
            The data from the yaml file.

        Returns
        -------
        obj_list: `list`[ `Any` ]
            A list of pydantic-backed model objects.
        """
        obj_list = []
        constructor = globals()[cls.__name__]
        for obj in data_dict:
            instance = constructor(**obj)
            obj_list.append(instance)
        return obj_list

    def _attach_metadata_cols(
        self, cameras: list[Camera], data: dict[str, Any]
    ) -> list[Camera]:
        """Attach metadata column heading data into individual cameras.

        Parameters
        ----------
        cameras : `list` [`Camera`]
            The list of camera objects.
        data : `dict` [`str`, `Any`]
            The data from the yaml file.

        Returns
        -------
        cams: `list`[`Camera`]
            The updated list of cameras.
        """
        updated_cams = []
        for cam in cameras:
            if cam.name in data and (cols := data[cam.name]):
                cam.metadata_cols = cols
            updated_cams.append(cam)
        return updated_cams

    def _inject_heartbeat_channels(
        self, heartbeats: list[Heartbeat]
    ) -> list[Heartbeat]:
        """Inject a camera's channels into each heartbeat wherever a camera
        name has been used as a reference in the creation of the heartbeat.

        Parameters
        ----------
        heartbeats : `list` [`Heartbeat`]
            A list of heartbeats.

        Returns
        -------
        hbs: `list`[`Heartbeat`]
            Updated heartbeats.
        """
        hbs = []
        for heartbeat in heartbeats:
            if cam_name := heartbeat.channels_as_cam_name:
                cam = next(
                    iter(cam for cam in self.cameras if cam.name == cam_name)
                )
                heartbeat.channels = cam.channels
            hbs.append(heartbeat)
        return hbs


def dict_from_list_of_named_objects(a_list: list[Any]) -> dict[str, Any]:
    return {obj.name: obj for obj in a_list if hasattr(obj, "name")}
