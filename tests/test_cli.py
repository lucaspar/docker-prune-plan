from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docker_prune_plan.docker_utils import (
    collect_used_images,
    collect_used_volumes,
    is_probably_anonymous_volume,
    normalize_image_id,
    short_id,
)
from docker_prune_plan.formatting import (
    human_size,
    parse_human_size_to_bytes,
    render_table,
)
from docker_prune_plan.models import PruneItem
from docker_prune_plan.planners import build_plan_image, build_plan_volume


# ---------------------------------------------------------------------------
# human_size()
# ---------------------------------------------------------------------------


class TestHumanSize:
    def test_zero(self) -> None:
        assert human_size(0) == "0B"

    def test_500_bytes(self) -> None:
        assert human_size(500) == "500B"

    def test_999_bytes(self) -> None:
        assert human_size(999) == "999B"

    def test_1000_bytes(self) -> None:
        # human_size strips ".0" from whole-number results
        assert human_size(1000) == "1kB"

    def test_1500_bytes(self) -> None:
        assert human_size(1500) == "1.5kB"

    def test_1_megabyte(self) -> None:
        assert human_size(1_000_000) == "1MB"

    def test_1_gigabyte(self) -> None:
        assert human_size(1_000_000_000) == "1GB"

    def test_negative_value(self) -> None:
        assert human_size(-500) == "-500B"

    def test_negative_large(self) -> None:
        assert human_size(-1_500) == "-1.5kB"


# ---------------------------------------------------------------------------
# parse_human_size_to_bytes()
# ---------------------------------------------------------------------------


class TestParseHumanSizeToBytes:
    def test_500b(self) -> None:
        assert parse_human_size_to_bytes("500B") == 500

    def test_1_5kb(self) -> None:
        assert parse_human_size_to_bytes("1.5kB") == 1500

    def test_10mb(self) -> None:
        assert parse_human_size_to_bytes("10MB") == 10_000_000

    def test_1gb(self) -> None:
        assert parse_human_size_to_bytes("1GB") == 1_000_000_000

    def test_1tb(self) -> None:
        assert parse_human_size_to_bytes("1TB") == 1_000_000_000_000

    def test_garbage_input(self) -> None:
        assert parse_human_size_to_bytes("garbage") is None

    def test_whitespace_padding(self) -> None:
        assert parse_human_size_to_bytes("  500 B  ") == 500


# ---------------------------------------------------------------------------
# short_id()
# ---------------------------------------------------------------------------


class TestShortId:
    def test_empty(self) -> None:
        assert short_id("") == ""

    def test_sha256_prefix(self) -> None:
        assert short_id("sha256:abc123def4567890") == "abc123def456"

    def test_bare_hex(self) -> None:
        assert short_id("abc123") == "abc123"


# ---------------------------------------------------------------------------
# normalize_image_id()
# ---------------------------------------------------------------------------


class TestNormalizeImageId:
    def test_empty(self) -> None:
        assert normalize_image_id("") == ""

    def test_bare_hex(self) -> None:
        assert normalize_image_id("abc123") == "sha256:abc123"

    def test_already_prefixed(self) -> None:
        assert normalize_image_id("sha256:abc123") == "sha256:abc123"


# ---------------------------------------------------------------------------
# is_probably_anonymous_volume()
# ---------------------------------------------------------------------------


class TestIsProbablyAnonymousVolume:
    def test_hex_32(self) -> None:
        assert is_probably_anonymous_volume("a" * 32) is True

    def test_hex_64(self) -> None:
        assert is_probably_anonymous_volume("a" * 64) is True

    def test_named_volume(self) -> None:
        assert is_probably_anonymous_volume("my-volume") is False

    def test_empty(self) -> None:
        assert is_probably_anonymous_volume("") is False


# ---------------------------------------------------------------------------
# collect_used_volumes()
# ---------------------------------------------------------------------------


class TestCollectUsedVolumes:
    def test_container_with_volume_mount(self) -> None:
        containers = [
            {"Mounts": [{"Type": "volume", "Name": "my-data"}]},
        ]
        assert collect_used_volumes(containers) == {"my-data"}

    def test_container_without_volume_mount(self) -> None:
        containers = [
            {"Mounts": [{"Type": "bind", "Source": "/host", "Destination": "/mnt"}]},
        ]
        assert collect_used_volumes(containers) == set()

    def test_container_no_mounts(self) -> None:
        containers = [{"Mounts": []}]
        assert collect_used_volumes(containers) == set()


# ---------------------------------------------------------------------------
# collect_used_images()
# ---------------------------------------------------------------------------


class TestCollectUsedImages:
    def test_container_with_image_id(self) -> None:
        containers = [{"ImageID": "sha256:abcdef1234567890"}]
        assert collect_used_images(containers) == {"sha256:abcdef1234567890"}

    def test_container_with_bare_hex_image(self) -> None:
        hex_id = "a" * 64
        containers = [{"Image": hex_id}]
        assert collect_used_images(containers) == {f"sha256:{hex_id}"}

    def test_container_with_name_image(self) -> None:
        containers = [{"Image": "nginx:latest"}]
        assert collect_used_images(containers) == set()


# ---------------------------------------------------------------------------
# render_table()
# ---------------------------------------------------------------------------


class TestRenderTable:
    def test_basic_rendering(self) -> None:
        items = [
            PruneItem(
                item_type="Container",
                item_id="abc123",
                name="my-app",
                size=1024,
                human_size="1.0kB",
                description="Stopped container",
            )
        ]
        table = render_table(items)
        assert "TYPE" in table
        assert "Container" in table
        assert "abc123" in table

    def test_excluded_columns(self) -> None:
        items = [
            PruneItem(
                item_type="Image",
                item_id="xyz",
                name="img",
                size=0,
                human_size="0B",
                description="dangling",
            )
        ]
        table = render_table(items, exclude_columns={"NAME"})
        assert "NAME" not in table
        assert "Image" in table

    def test_empty_list(self) -> None:
        table = render_table([])
        # Should still produce a header row
        assert "TYPE" in table


# ---------------------------------------------------------------------------
# PruneItem.to_dict()
# ---------------------------------------------------------------------------


class TestPruneItemToDict:
    def test_returns_all_keys(self) -> None:
        item = PruneItem(
            item_type="Network",
            item_id="net1",
            name="mynet",
            size=0,
            human_size="0B",
            description="Unused network",
        )
        d = item.to_dict()
        assert d["type"] == "Network"
        assert d["id"] == "net1"
        assert d["name"] == "mynet"
        assert d["size"] == 0
        assert d["human_size"] == "0B"
        assert d["description"] == "Unused network"
        assert set(d.keys()) == {
            "type",
            "id",
            "name",
            "size",
            "human_size",
            "description",
        }


# ---------------------------------------------------------------------------
# build_plan_image() — sorting verification
# ---------------------------------------------------------------------------


class TestBuildPlanImageSorting:
    def test_returns_items_sorted_by_size_descending(self) -> None:
        client = MagicMock()
        # No containers → nothing used
        client.containers.return_value = []
        # Two images: small first, large second
        client.images.return_value = [
            {
                "Id": "sha256:small111111111111",
                "Size": 100,
                "RepoTags": ["small:latest"],
                "Created": 0,
            },
            {
                "Id": "sha256:large222222222222",
                "Size": 5000,
                "RepoTags": ["large:latest"],
                "Created": 0,
            },
        ]
        plan, total = build_plan_image(client, include_all=False)
        sizes = [item.size for item in plan]
        assert sizes == sorted(sizes, reverse=True)
        assert total == 5100


# ---------------------------------------------------------------------------
# build_plan_volume() — sorting verification
# ---------------------------------------------------------------------------


class TestBuildPlanVolumeSorting:
    def test_returns_items_sorted_by_size_descending(self) -> None:
        client = MagicMock()
        client.containers.return_value = []
        client.df.return_value = {
            "Volumes": [
                {
                    "Name": "a" * 32,
                    "UsageData": {"Size": 200},
                },
                {
                    "Name": "b" * 32,
                    "UsageData": {"Size": 1000},
                },
                {
                    "Name": "c" * 32,
                    "UsageData": {"Size": 50},
                },
            ]
        }
        plan, total = build_plan_volume(client, include_all=False, system_mode=False)
        sizes = [item.size for item in plan]
        assert sizes == [1000, 200, 50]
        assert total == 1250
