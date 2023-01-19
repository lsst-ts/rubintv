from pathlib import Path
from typing import Any, Dict

import yaml
from dacite import from_dict

from .models import Camera, Location


class ModelInitator:
    def __init__(self) -> None:
        models_file_path = Path(__file__).parent / "models_data.yml"
        with open(models_file_path, "r") as file:
            data = yaml.safe_load(file)
        self._cameras = self._get_cameras(data)
        self._locations = self._get_locations(data)
        self._services = self._get_services(data)

    @property
    def cameras(self) -> Dict[str, Camera]:
        return self._cameras

    @property
    def locations(self) -> Dict[str, Location]:
        return self._locations

    @property
    def services(self) -> Dict[str, Any]:
        return self._services

    def _get_cameras(self, data: Dict) -> Dict[str, Camera]:
        cameras = {}
        d_cameras = data["Cameras"]
        for cam_name, cam in d_cameras.items():
            # makes Camera objects from dictionaries
            cam = from_dict(Camera, cam)
            cam.slug = cam_name
            # insert lowercase Channel name as 'simplename'
            for chan in cam.channels:
                cam.channels[chan].simplename = chan
            cameras[cam_name] = cam
        return cameras

    def _get_locations(self, data: Dict) -> Dict[str, Location]:
        locations = {}
        d_locations = data["Locations"]
        for loc_name, loc in d_locations.items():
            location = from_dict(Location, loc)
            location.slug = loc_name
            locations[loc_name] = location
        return locations

    def _get_services(self, data: Dict) -> Dict[str, Any]:
        production_services: dict[str, Any] = data["Services"]
        for s in production_services:
            if "channels" in production_services[s]:
                # expand name of camera out into camera's channels
                cam = production_services[s]["channels"]
                chans = self._cameras[cam].channels
                production_services[s]["channels"] = chans
        return production_services
