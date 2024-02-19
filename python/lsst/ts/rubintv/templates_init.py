from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, select_autoescape
from lsst.ts.rubintv import __version__
from lsst.ts.rubintv.models.models_helpers import get_image_viewer_link
from lsst.ts.rubintv.models.models_init import (
    dict_from_list_of_named_objects as list_to_dict,
)

__all__ = ["get_templates"]


def get_templates() -> Jinja2Templates:
    env = Environment(
        autoescape=select_autoescape(),
        auto_reload=True,
    )
    # Prevent tojson() filter from re-ordering keys.
    env.policies["json.dumps_kwargs"] = {"sort_keys": False}
    # Add filter to convert lists to dicts.
    env.filters["list_to_dict"] = list_to_dict
    env.globals["viewer_link"] = get_image_viewer_link
    # Inject version as template global.
    env.globals.update(version=__version__)

    # point jinja2 to the templates dir.
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates", env=env)

    return templates
