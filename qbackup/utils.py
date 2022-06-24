"""
Utility functions
"""

from dataclasses import asdict, fields
from io import TextIOWrapper
from typing import Dict, List, Text

from .api import AbstractDataManager


def dump_as_table(
    fp: TextIOWrapper,
    headers: List[Text],
    lines: List[List[Text]],
    dump_headers: bool = True,
) -> None:
    # Store the size of the larger item in `lines`,
    # for each header in `headers`.
    # It is first initialized with -1 to ease further comparison
    largest_items: Dict[Text, int] = {header: 0 for header in headers}

    for line in lines:
        if len(line) != len(headers):
            raise ValueError(
                "Found a line lenght different than the header lenght. "
                f"Header length: {len(headers)}, line length: {len(line)}"
            )

        # Try to find the larger item in length
        for header, item in zip(headers, line):
            item_str = str(item)
            if len(item_str) > largest_items[header]:
                largest_items[header] = len(item_str)

    placeholder_list: List[str] = []

    # Create the placeholders expected by `str.format()`
    for size in largest_items.values():
        placeholder_list.append("".join(["{:<", str(size), "}"]))

    # Separate each field by a TAB. Compliant with `cut` and `awk`
    # and most shell programs
    placeholder = "\t".join(placeholder_list)

    all_lines = []

    if dump_headers:
        all_lines.append(placeholder.format(*headers))

    for line in lines:
        all_lines.append(placeholder.format(*line))

    # Write all separated and trailed by a line feed 
    fp.write("\n".join(all_lines) + "\n")


class PrettyDumpModels:
    def __init__(
        self, fp: TextIOWrapper, manager: AbstractDataManager
    ) -> None:
        self.fp = fp
        self._manager = manager
        self._headers = [
            field.name for field in fields(manager._model_factory)
        ]

    def fetch_and_dump_list(self) -> None:
        models = self._manager.list()
        lines = []

        for model in models:
            lines.append(asdict(model).values())

        self.dump_list(lines)

    def dump_one(self, data) -> None:
        self.dump_list([data])

    def dump_list(self, data: List) -> None:
        dump_as_table(self.fp, self._headers, data)
