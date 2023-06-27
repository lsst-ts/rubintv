from typing import Any, Iterable

__all__ = ["find_first", "find_all"]


async def find_first(a_list: list[Any], key: str, to_match: str) -> Any | None:
    result = None
    if iterator := await _find_by_key_and_value(a_list, key, to_match):
        try:
            result = next(iter(iterator))
        except StopIteration:
            pass
    return result


async def find_all(
    a_list: list[Any], key: str, to_match: str
) -> list[Any] | None:
    result = None
    if iterator := await _find_by_key_and_value(a_list, key, to_match):
        result = list(iterator)
    return result


async def _find_by_key_and_value(
    a_list: list[Any], key: str, to_match: str
) -> Iterable[Any] | None:
    result = None
    if not a_list:
        return None
    try:
        result = (o for o in a_list if o.dict()[key] == to_match)
    except IndexError:
        pass
    return result
