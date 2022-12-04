from typing import Any

import yaml
from dacite import from_dict
from from_root import from_here

from .models import Camera, Location

models_file_path = from_here("models_data.yml")
with open(models_file_path, "r") as file:
    d = yaml.safe_load(file)

cameras = {}
d_cameras = d["Cameras"]
for cam_name, cam in d_cameras.items():
    # makes Camera objects from dictionaries
    cam = from_dict(Camera, cam)
    cam.slug = cam_name
    # insert lowercase Channel name as 'simplename'
    for chan in cam.channels:
        cam.channels[chan].simplename = chan
    cameras[cam_name] = cam

locations = {}
d_locations = d["Locations"]
for loc_name, loc in d_locations.items():
    location = from_dict(Location, loc)
    location.slug = loc_name
    locations[loc_name] = location

production_services: dict[str, Any] = d["Services"]
for s in production_services:
    if "channels" in production_services[s]:
        # expand name of camera out into camera's channels
        cam = production_services[s]["channels"]
        chans = cameras[cam].channels
        production_services[s]["channels"] = chans
