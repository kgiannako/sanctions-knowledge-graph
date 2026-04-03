from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Entity:
    id: str
    entity_type: str               # Person | Organisation | Vessel
    primary_name: str
    aliases: list[str] = field(default_factory=list)
    nationality: Optional[str] = None
    dob: Optional[str] = None
    imo_number: Optional[str] = None
    source: str = ""
    programs: list[str] = field(default_factory=list)
    raw_addresses: list[str] = field(default_factory=list)

@dataclass
class Relationship:
    source_id: str
    target_id: str
    rel_type: str                  # OWNS | CONTROLS | ASSOCIATED_WITH | LISTED_BY
    attributes: dict = field(default_factory=dict)