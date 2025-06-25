from itertools import chain
from pathlib import Path
from typing import Any, Type

import yaml
from lsst.ts.rubintv.config import config, rubintv_logger
from lsst.ts.rubintv.models.models import Camera, Channel, Location
from lsst.ts.rubintv.models.models_helpers import find_first
from pydantic import BaseModel

__all__ = ["ModelsInitiator"]

logger = rubintv_logger()


class ModelsInitiator:
    """Loads and substantiates models with data from a yaml file.

        Instance variables
    -    ------------------
    -    self.locations : `List` [`Location`]
    -        The locations or sites where the cameras are based.
    -    self.cameras : `List` [`Camera`]
    -        The cameras.
    """

    def __init__(self) -> None:
        models_file_path = Path(__file__).parent / "models_data.yaml"
        with open(models_file_path, "r") as file:
            data = yaml.safe_load(file)

        cameras = self._populate_model(Camera, data["cameras"])
        self.cameras = self._attach_metadata_cols(cameras, data)

        current_location = config.site_location
        i_can_see = data["bucket_configurations"][current_location]
        all_locations = self._populate_model(Location, data["locations"])
        locations = [loc for loc in all_locations if loc.name in i_can_see]
        # sort locations to satisfy the order in which they are listed in
        # bucket_configurations
        locations.sort(key=lambda loc: i_can_see.index(loc.name))

        self.locations = self._attach_cameras_to_locations(self.cameras, locations)

        self.services = self._init_services(cameras, data["services"])

        # This is a list of usernames to authorize for admin access at the
        # current Location.
        self.admin_list = data["admin_for"][current_location]
        self.redis_detectors = data["redis_detectors"]

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

    def _attach_metadata_cols(self, cameras: list[Camera], data: Any) -> list[Camera]:
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

    def _init_services(
        self, cameras: list[Camera], services: dict
    ) -> dict[str, dict[str, str] | list[Channel]]:
        for s in services:
            if "channels" in services[s]:
                # expand name of camera out into camera's channels
                cam_name = services[s]["channels"]
                camera: Camera | None = find_first(cameras, "name", cam_name)
                if camera is not None:
                    channels: list[Channel] = camera.channels
                    services[s]["channels"] = channels
        return services
