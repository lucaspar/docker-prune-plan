from __future__ import annotations

import re
from typing import Sequence

from docker_prune_plan.models import PruneItem


def human_size(num: int) -> str:
    if num == 0:
        return "0B"
    suffixes = ["B", "kB", "MB", "GB", "TB", "PB", "EB"]
    negative = num < 0
    value = abs(float(num))
    suffix = suffixes[0]
    for suffix in suffixes:
        if value < 1000 or suffix == suffixes[-1]:
            break
        value /= 1000.0
    formatted = f"{value:.1f}{suffix}"
    if formatted.endswith(".0" + suffix):
        formatted = formatted.replace(".0" + suffix, suffix)
    return f"-{formatted}" if negative else formatted


def parse_human_size_to_bytes(text: str) -> int | None:
    match = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*([KMGTP]?B)\s*$", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "PB": 1000**5,
    }
    return int(value * multipliers.get(unit, 1))


def render_table(
    items: Sequence[PruneItem], exclude_columns: set[str] | None = None
) -> str:
    if exclude_columns is None:
        exclude_columns = set()
    all_headers = ["TYPE", "ID", "NAME", "SIZE", "INFO"]
    headers = [h for h in all_headers if h not in exclude_columns]
    column_indices = [i for i, h in enumerate(all_headers) if h not in exclude_columns]

    rows: list[list[str]] = [
        [item.item_type, item.item_id, item.name, item.human_size, item.description]
        for item in items
    ]
    rows = [[row[i] for i in column_indices] for row in rows]

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))
    lines = ["  ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers)))]
    for row in rows:
        lines.append(
            "  ".join(str(row[idx]).ljust(widths[idx]) for idx in range(len(headers)))
        )
    return "\n".join(lines)
