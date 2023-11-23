import os
from itertools import chain
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic import BaseModel

from rubintv.models.models import Camera, Location
from rubintv.models.models_helpers import find_first

__all__ = ["ModelsInitiator", "dict_from_list_of_named_objects"]


class ModelsInitiator:
    """Loads and substantiates models with data from a yaml file.

        Instance variables
    -    ------------------
    -    self.locations : `List` [`Location`]
    -        The locations or sites where the cameras ar based.
    -    self.cameras : `List` [`Camera`]
    -        The cameras.
    """

    def __init__(self) -> None:
        models_file_path = Path(__file__).parent / "models_data.yaml"
        with open(models_file_path, "r") as file:
            data = yaml.safe_load(file)
        cameras = self._populate_model(Camera, data["cameras"])
        self.cameras = self._attach_metadata_cols(cameras, data)
        current_location = where_am_i()
        i_can_see = data["bucket_configurations"][current_location]
        all_locations = self._populate_model(Location, data["locations"])
        locations = [loc for loc in all_locations if loc.name in i_can_see]
        self.locations = self._attach_cameras_to_locations(
            self.cameras, locations
        )

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
        self, cameras: list[Camera], data: Any
    ) -> list[Camera]:
        """Attach metadata column heading data to individual cameras.

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
        metadata: dict[str, Any] = data["metadata_cols"]
        updated_cams: list[Camera] = []
        for cam in cameras:
            if cam.name in metadata and (cols := metadata[cam.name]):
                cam.metadata_cols = cols
            updated_cams.append(cam)
        return updated_cams


def where_am_i() -> str:
    location = os.getenv("RAPID_ANALYSIS_LOCATION", "")
    if location == "TTS":
        return "tucson"
    if location == "SUMMIT":
        return "summit"
    if location == "USDF":
        return "usdf-k8s"
    if os.getenv("GITHUB_ACTIONS", ""):
        return "gha"
    else:
        return "local"


def dict_from_list_of_named_objects(a_list: list[Any]) -> dict[str, Any]:
    return {obj.name: obj for obj in a_list if hasattr(obj, "name")}
