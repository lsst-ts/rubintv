import yaml
from dacite import from_dict

from .models import Camera, Location

# TODO: find a better way of locating yaml file
with open("src/rubintv/models/models_data.yml", "r") as file:
    d = yaml.safe_load(file)

cameras = {}
d_cameras = d["Cameras"]
for cam_name in d_cameras:
    cam = from_dict(Camera, d_cameras[cam_name])
    cam.slug = cam_name
    # insert lowercase camera name as 'simplename'
    for chan in cam.channels:
        cam.channels[chan].simplename = chan
    cameras[cam_name] = cam

locations = {}
d_locations = d["Locations"]
for loc_name in d_locations:
    location = Location(d_locations[loc_name]["name"])
    location.slug = loc_name

    d_camera_groups = d_locations[loc_name]["cameras"]
    camera_groups = {}
    for cam_group in d_camera_groups:
        this_group = d_camera_groups[cam_group]
        cams_in_group: list[str] = [
            cameras[cam_name].slug for cam_name in this_group
        ]
        camera_groups[cam_group] = cams_in_group
    location.camera_groups = camera_groups

    locations[loc_name] = location

production_services = d["Services"]
for s in production_services:
    if "channels" in production_services[s]:
        # expand name of camera out into camera's channels
        cam = production_services[s]["channels"]
        chans = cameras[cam].channels
        production_services[s]["channels"] = chans
