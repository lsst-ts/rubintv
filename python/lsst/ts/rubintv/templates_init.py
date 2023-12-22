from pathlib import Path

from fastapi.templating import Jinja2Templates
from lsst.ts.rubintv import __version__
from lsst.ts.rubintv.models.models_helpers import get_image_viewer_link
from lsst.ts.rubintv.models.models_init import (
    dict_from_list_of_named_objects as list_to_dict,
)

__all__ = ["get_templates"]


def get_templates() -> Jinja2Templates:
    # point jinja2 to the templates dir.
    templates = Jinja2Templates(
        directory=Path(__file__).parent / "templates",
        autoescape=False,
        auto_reload=True,
    )
    # Prevent tojson() filter from re-ordering keys.
    templates.env.policies["json.dumps_kwargs"] = {"sort_keys": False}

    # Add filter to convert lists to dicts.
    templates.env.filters["list_to_dict"] = list_to_dict
    templates.env.globals["viewer_link"] = get_image_viewer_link

    # Inject version as template global.
    templates.env.globals.update(version=__version__)

    return templates
