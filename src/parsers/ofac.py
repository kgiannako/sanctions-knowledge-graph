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
        country = None
        for addr in entry.findall(f".//{tag('address')}"):
            parts = [text(addr, "address1"), text(addr, "city"), text(addr, "country")]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)
            if not country:
                country = text(addr, "country")

        nationality = None
        for nat in entry.findall(f".//{tag('nationality')}"):
            nationality = text(nat, "country")
            break

        dob = None
        for dob_item in entry.findall(f".//{tag('dateOfBirthItem')}"):
            dob = text(dob_item, "dateOfBirth")
            break

        # fixed IMO extraction
        imo = None
        for id_el in entry.findall(f".//{tag('id')}"):
            id_type = text(id_el, "idType") or ""
            id_number = text(id_el, "idNumber") or ""
            if "IMO" in id_number.upper() or "vessel registration" in id_type.lower():
                imo = id_number.replace("IMO ", "").strip()
                break

        # vessel specific fields
        vessel_flag = None
        vessel_type = None
        vessel_owner = None
        tonnage = None
        vessel_info = entry.find(tag("vesselInfo"))
        if vessel_info is not None:
            vessel_flag = text(vessel_info, "vesselFlag")
            vessel_type = text(vessel_info, "vesselType")
            vessel_owner = text(vessel_info, "vesselOwner")
            tonnage = text(vessel_info, "grossRegisteredTonnage")

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
            country=country,
            vessel_flag=vessel_flag,
            vessel_type=vessel_type,
            vessel_owner=vessel_owner,
            tonnage=tonnage,
        )
        entities.append(entity)

    return entities, relationships