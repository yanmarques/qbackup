from unittest.mock import Mock
from qbackup.utils import dump_as_table


def test_dump_lines_respecting_largest_item():
    fp = Mock()
    headers = ["Name", "Age", "City"]
    lines = [
        ["John", "999", "No Where"],
        ["Manoela", "111", "A city"],
    ]

    expected_dump = "\n".join([
        "Name    Age City    ",
        "John    999 No Where",
        "Manoela 111 A city  ",
    ])

    dump_as_table(fp, headers, lines)

    fp.write.assert_called_once_with(expected_dump)


def test_dump_only_headers_when_empty_lines():
    fp = Mock()
    headers = ["Name", "Age", "City"]
    lines = []

    expected_dump = "Name Age City"

    dump_as_table(fp, headers, lines)

    fp.write.assert_called_once_with(expected_dump)
