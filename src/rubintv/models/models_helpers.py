from datetime import date

__all__ = ["get_prefix_from_date"]


def get_prefix_from_date(prefix: str, a_date: date) -> str:
    """Returns a string prefix for searching in GCS buckets
    for files belonging to a given channel and date.

    Parameters
    ----------
    prefix : `str`
        The prefix for a particular channel.
    a_date : `date`
        The given date to use to form the prefix. The date format is
        `"YYYY-MM-DD"` as output by `datetime.date` on conversion to a `str`.

    Returns
    -------
    new_prefix : `str`
        The correctly formed prefix used for bucket lookup.
    """
    prefix_dashes = prefix.replace("_", "-")
    new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{a_date}_seqNum_"
    return new_prefix


def string_int_to_date(date_string: str) -> date:
    """Returns a date object from a given date string in the
    form ``"YYYYMMDD"``.

    Parameters
    ----------
    date_string : `str`
        A date string in the form ``"YYYYMMDD"``.

    Returns
    -------
    `date`
        A date.
    """
    d = date_string
    return date(int(d[0:4]), int(d[4:6]), int(d[6:8]))
