from typing import Any, Iterable

__all__ = ["find_first", "find_all"]


def find_first(a_list: list[Any], key: str, to_match: str) -> Any | None:
    result = None
    if iterator := _find_by_key_and_value(a_list, key, to_match):
        try:
            result = next(iter(iterator))
        except StopIteration:
            pass
    return result


def find_all(a_list: list[Any], key: str, to_match: str) -> list[Any] | None:
    result = None
    if iterator := _find_by_key_and_value(a_list, key, to_match):
        result = list(iterator)
    return result


def _find_by_key_and_value(
    a_list: list[Any], key: str, to_match: str
) -> Iterable[Any] | None:
    result = None
    if not a_list:
        return None
    try:
        result = (o for o in a_list if o.model_dump()[key] == to_match)
    except IndexError:
        pass
    return result
