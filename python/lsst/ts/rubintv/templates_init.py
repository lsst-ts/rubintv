from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from lsst.ts.rubintv import __version__
from lsst.ts.rubintv.config import config
from lsst.ts.rubintv.models.models_helpers import (
    dict_from_list_of_named_objects as list_to_dict,
)
from lsst.ts.rubintv.models.models_helpers import get_image_viewer_link

__all__ = ["get_templates"]


def get_templates() -> Jinja2Templates:
    loader = FileSystemLoader(Path(__file__).parent / "templates")

    env = Environment(autoescape=True, auto_reload=True, loader=loader)

    # Prevent tojson() filter from re-ordering keys.
    env.policies["json.dumps_kwargs"] = {"sort_keys": False}

    # Add filter to convert lists to dicts.
    env.filters["list_to_dict"] = list_to_dict
    env.globals["viewer_link"] = get_image_viewer_link

    # Inject version etc. as template globals.
    env.globals.update(
        {
            "version": __version__,
            "site_location": config.site_location,
            "path_prefix": config.path_prefix,
        }
    )

    templates = Jinja2Templates(env=env)

    return templates
