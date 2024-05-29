from calendar import Calendar
from datetime import date
from typing import Any

from lsst.ts.rubintv.models.models import NightReportPayload


def month_names() -> list[str]:
    """Returns a list of month names as words.

    Returns
    -------
    List[str]
        A list of month names.
    """
    return [date(2000, m, 1).strftime("%B") for m in list(range(1, 13))]


def calendar_factory() -> Calendar:
    # first weekday 0 is Monday
    calendar = Calendar(firstweekday=0)
    return calendar


def build_title(*title_parts: str) -> str:
    title = "RubinTV"
    to_append = " - ".join(title_parts)
    if to_append:
        title += " - " + to_append
    return title


def to_dict(object: Any | None) -> dict | None:
    if object is None:
        return None
    return object.__dict__


async def night_report_to_dict(
    nr_payload: NightReportPayload,
) -> dict[str, dict | list[dict]]:
    if not nr_payload:
        return {}
    plots = []
    for plot in nr_payload.get("plots", []):
        plots.append(plot.__dict__)
    return {"text": nr_payload.get("text", {}), "plots": plots}
