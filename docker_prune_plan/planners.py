from __future__ import annotations

from datetime import datetime, timezone

import docker
from docker.errors import DockerException

from docker_prune_plan.docker_utils import (
    collect_used_images,
    collect_used_volumes,
    is_probably_anonymous_volume,
    normalize_image_id,
    short_id,
)
from docker_prune_plan.formatting import human_size
from docker_prune_plan.models import PruneItem


def build_plan_container(client: docker.APIClient) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0
    stopped = client.containers(
        all=True, filters={"status": ["created", "exited", "dead"]}, size=True
    )
    for container in stopped:
        names = container.get("Names") or []
        name = names[0].lstrip("/") if names else ""
        status = container.get("Status") or ""
        size = int(container.get("SizeRw") or 0)
        total += size
        plan.append(
            PruneItem(
                item_type="Container",
                item_id=short_id(container.get("Id") or ""),
                name=name,
                size=size,
                human_size=human_size(size),
                description=f"Status: {status}" if status else "Stopped container",
            )
        )
    return plan, total


def build_plan_image(
    client: docker.APIClient, include_all: bool
) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0
    all_containers = client.containers(all=True)
    used_images = collect_used_images(all_containers)

    img_filters = {"dangling": True} if not include_all else {}
    images = client.images(all=True, filters=img_filters)

    for image in images:
        image_id = image.get("Id") or ""
        if include_all and image_id in used_images:
            continue

        size = int(image.get("Size") or 0)
        total += size

        tags = image.get("RepoTags") or []
        name = ", ".join(tags) if tags else "<none>"

        created = image.get("Created")
        created_str = ""
        if isinstance(created, (int, float)) and created > 0:
            created_str = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()

        reason = "Dangling image" if not include_all else "Unused image (no containers)"
        desc = reason
        if created_str:
            desc = f"{reason}; Created: {created_str}"

        plan.append(
            PruneItem(
                item_type="Image",
                item_id=short_id(image_id),
                name=name,
                size=size,
                human_size=human_size(size),
                description=desc,
            )
        )

    plan.sort(key=lambda item: item.size, reverse=True)
    return plan, total


def build_plan_volume(
    client: docker.APIClient, include_all: bool, system_mode: bool
) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0

    all_containers = client.containers(all=True)
    used_volumes = collect_used_volumes(all_containers)

    df_data = client.df()
    volumes = df_data.get("Volumes") or []

    for volume in volumes:
        name = volume.get("Name") or ""
        if not name or name in used_volumes:
            continue

        if not include_all and not is_probably_anonymous_volume(name):
            continue

        usage = volume.get("UsageData") or {}
        size = int(usage.get("Size") or 0)
        total += size

        if system_mode:
            reason = "Unused volume (anonymous)"
        else:
            reason = "Unused volume (anonymous)" if not include_all else "Unused volume"

        plan.append(
            PruneItem(
                item_type="Volume",
                item_id=name,
                name=name,
                size=size,
                human_size=human_size(size),
                description=reason,
            )
        )

    plan.sort(key=lambda item: item.size, reverse=True)
    return plan, total


def build_plan_network(client: docker.APIClient) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0

    networks = client.networks()
    for net in networks:
        net_id = net.get("Id") or ""
        name = net.get("Name") or ""
        if name in {"bridge", "host", "none"}:
            continue

        try:
            info = client.inspect_network(net_id)
        except DockerException:
            continue

        containers = info.get("Containers") or {}
        if containers:
            continue

        plan.append(
            PruneItem(
                item_type="Network",
                item_id=short_id(net_id),
                name=name,
                size=0,
                human_size="0B",
                description="Unused network",
            )
        )

    return plan, total


def build_plan_build_cache(client: docker.APIClient) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0
    df_data = client.df()
    build_cache = df_data.get("BuildCache") or []
    for entry in build_cache:
        if entry.get("InUse"):
            continue
        size = int(entry.get("Size") or 0)
        total += size
        build_id = entry.get("ID") or ""
        desc = entry.get("Description") or ""
        last_used = entry.get("LastUsedAt") or ""
        info = "; ".join([p for p in [desc, f"Last used: {last_used}"] if p])
        plan.append(
            PruneItem(
                item_type="BuildCache",
                item_id=short_id(build_id),
                name=desc,
                size=size,
                human_size=human_size(size),
                description=info,
            )
        )
    return plan, total


def build_plan_system(
    client: docker.APIClient, include_all_images: bool, include_volumes: bool
) -> tuple[list[PruneItem], int]:
    plan: list[PruneItem] = []
    total = 0

    items, t = build_plan_container(client)
    plan.extend(items)
    total += t

    items, t = build_plan_network(client)
    plan.extend(items)
    total += t

    items, t = build_plan_image(client, include_all_images)
    plan.extend(items)
    total += t

    if include_volumes:
        items, t = build_plan_volume(client, include_all=False, system_mode=True)
        plan.extend(items)
        total += t

    items, t = build_plan_build_cache(client)
    plan.extend(items)
    total += t

    return plan, total
