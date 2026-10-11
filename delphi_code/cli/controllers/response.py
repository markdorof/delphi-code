from typing import NamedTuple

from ..terminal.text_layout import TextView


class ControllerResponse(NamedTuple):
    data: dict
    views: list[TextView]
