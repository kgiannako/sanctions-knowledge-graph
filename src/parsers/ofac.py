import xml.etree.ElementTree as ET
from src.models import Entity, Relationship

TYPE_MAP = {
    "Individual": "Person",
    "Entity": "Organisation",
    "Vessel": "Vessel"
}

NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML"

def tag(name: str) -> str:
    return f"{{{NS}}}{name}"

def text(element, name: str) -> str | None:
    el = element.find(tag(name))
    return el.text if el is not None else None

def parse_ofac(path: str) -> tuple[list[Entity], list[Relationship]]:
    tree = ET.parse(path)
    root = tree.getroot()
    entities = []
    relationships = []

    for entry in root.findall(tag("sdnEntry")):
        uid = text(entry, "uid")
        etype = text(entry, "sdnType")
        last_name = text(entry, "lastName") or ""
        first_name = text(entry, "firstName") or ""
        primary_name = f"{first_name} {last_name}".strip() if first_name else last_name

        aliases = []
        for aka in entry.findall(f".//{tag('aka')}"):
            aka_last = text(aka, "lastName") or ""
            aka_first = text(aka, "firstName") or ""
            alias = f"{aka_first} {aka_last}".strip() if aka_first else aka_last
            if alias:
                aliases.append(alias)

        programs = [
            el.text for el in entry.findall(f".//{tag('program')}") if el.text
        ]

        addresses = []
        for addr in entry.findall(f".//{tag('address')}"):
            parts = [text(addr, "address1"), text(addr, "city"), text(addr, "country")]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)

        nationality = None
        for nat in entry.findall(f".//{tag('nationality')}"):
            nationality = text(nat, "country")
            break

        dob = None
        for dob_item in entry.findall(f".//{tag('dateOfBirthItem')}"):
            dob = text(dob_item, "dateOfBirth")
            break

        imo = None
        for id_el in entry.findall(f".//{tag('id')}"):
            if text(id_el, "idType") == "IMO Number":
                imo = text(id_el, "idNumber")
                break

        entity = Entity(
            id=f"ofac_{uid}",
            entity_type=TYPE_MAP.get(etype, "Organisation"),
            primary_name=primary_name,
            aliases=aliases,
            nationality=nationality,
            dob=dob,
            imo_number=imo,
            source="ofac",
            programs=programs,
            raw_addresses=addresses,
        )
        entities.append(entity)

    return entities, relationships