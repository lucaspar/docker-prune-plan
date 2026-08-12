from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import docker
from docker.errors import DockerException
from docker.utils import kwargs_from_env

from docker_prune_plan.formatting import human_size, render_table
from docker_prune_plan.planners import (
    build_plan_container,
    build_plan_image,
    build_plan_network,
    build_plan_system,
    build_plan_volume,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="docker-prune-plan",
        description=(
            "Preview what docker prune commands would remove, grouped by resource type "
            "and reclaimable space."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_image = sub.add_parser(
        "image",
        help="list images that would be pruned",
        description="Show dangling or unused images and their reclaimable space.",
    )
    p_image.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include unused images referenced by no containers (not just dangling images).",
    )
    p_image.add_argument(
        "--json",
        action="store_true",
        help="Output the plan as JSON instead of a table.",
    )

    p_volume = sub.add_parser(
        "volume",
        help="list volumes that would be pruned",
        description="Show unused volumes and their reclaimable space.",
    )
    p_volume.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include named volumes; by default only anonymous volumes are included.",
    )
    p_volume.add_argument(
        "--json",
        action="store_true",
        help="Output the plan as JSON instead of a table.",
    )

    p_container = sub.add_parser(
        "container",
        help="list stopped containers that would be pruned",
        description="Show stopped containers eligible for pruning and their reclaimable space.",
    )
    p_container.add_argument(
        "--json",
        action="store_true",
        help="Output the plan as JSON instead of a table.",
    )

    p_network = sub.add_parser(
        "network",
        help="list unused networks that would be pruned",
        description="Show user-defined networks with no attached containers.",
    )
    p_network.add_argument(
        "--json",
        action="store_true",
        help="Output the plan as JSON instead of a table.",
    )

    p_system = sub.add_parser(
        "system",
        help="list everything that would be pruned",
        description=(
            "Show containers, networks, images, optional volumes, and build cache "
            "that would be removed by docker system prune."
        ),
    )
    p_system.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include unused images referenced by no containers (not just dangling images).",
    )
    p_system.add_argument(
        "--volumes",
        action="store_true",
        help="Include unused volumes in the plan (matches docker system prune --volumes).",
    )
    p_system.add_argument(
        "--name",
        action="store_true",
        help="Show the NAME column in the system plan output table.",
    )
    p_system.add_argument(
        "--json",
        action="store_true",
        help="Output the plan as JSON instead of the table default.",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        client = docker.APIClient(version="auto", **kwargs_from_env())
    except DockerException as exc:
        print(f"Error connecting to Docker: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.cmd == "container":
            plan, plan_total = build_plan_container(client)

        elif args.cmd == "network":
            plan, plan_total = build_plan_network(client)

        elif args.cmd == "image":
            plan, plan_total = build_plan_image(client, include_all=bool(args.all))

        elif args.cmd == "volume":
            plan, plan_total = build_plan_volume(
                client, include_all=bool(args.all), system_mode=False
            )

        elif args.cmd == "system":
            plan, plan_total = build_plan_system(
                client,
                include_all_images=bool(args.all),
                include_volumes=bool(args.volumes),
            )

        else:
            raise SystemExit(2)

    except DockerException as exc:
        print(f"Docker error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()

    if args.json:
        out = {
            "command": args.cmd,
            "items": [i.to_dict() for i in plan],
            "plan_reclaimable_bytes": plan_total,
        }
        print(json.dumps(out, indent=2))
        return

    exclude_columns: set[str] = set()
    if args.cmd == "system" and not args.name:
        exclude_columns.add("NAME")

    print(render_table(plan, exclude_columns=exclude_columns))
    print(f"\nPlan Reclaimable Space: {human_size(plan_total)}")


if __name__ == "__main__":
    main()
