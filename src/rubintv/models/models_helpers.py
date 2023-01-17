from datetime import date

__all__ = ["get_prefix_from_date"]


def get_prefix_from_date(prefix: str, a_date: date) -> str:
    prefix_dashes = prefix.replace("_", "-")
    new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{a_date}_seqNum_"
    return new_prefix


def string_int_to_date(date_string: str) -> date:
    d = date_string
    return date(int(d[0:4]), int(d[4:6]), int(d[6:8]))
