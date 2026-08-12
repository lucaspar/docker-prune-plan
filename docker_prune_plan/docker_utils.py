from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


def short_id(full_id: str) -> str:
    if not full_id:
        return ""
    if full_id.startswith("sha256:"):
        full_id = full_id.split(":", 1)[1]
    return full_id[:12]


def normalize_image_id(v: str) -> str:
    if not v:
        return ""
    return v if v.startswith("sha256:") else f"sha256:{v}"


def collect_used_volumes(containers: Sequence[Mapping[str, object]]) -> set[str]:
    used: set[str] = set()
    for container in containers:
        for mount in container.get("Mounts", []) or []:
            if mount.get("Type") == "volume" and mount.get("Name"):
                used.add(str(mount["Name"]))
    return used


def collect_used_images(containers: Sequence[Mapping[str, object]]) -> set[str]:
    used: set[str] = set()
    for container in containers:
        image_id = container.get("ImageID")
        if image_id:
            used.add(normalize_image_id(str(image_id)))
            continue

        v = container.get("Image")
        if v:
            sv = str(v)
            if sv.startswith("sha256:") or re.fullmatch(r"[0-9a-f]{64}", sv):
                used.add(normalize_image_id(sv))
    return used


def is_probably_anonymous_volume(name: str) -> bool:
    if not name:
        return False
    return re.fullmatch(r"[0-9a-f]{32,64}", name) is not None
