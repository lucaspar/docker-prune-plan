from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PruneItem:
    item_type: str
    item_id: str
    name: str = ""
    size: int = 0
    human_size: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.item_type,
            "id": self.item_id,
            "name": self.name,
            "size": self.size,
            "human_size": self.human_size,
            "description": self.description,
        }
