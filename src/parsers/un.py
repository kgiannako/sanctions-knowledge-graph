import xml.etree.ElementTree as ET
from src.models import Entity, Relationship

TYPE_MAP = {
    "individual": "Person",
    "entity": "Organisation",
    "vessel": "Vessel"
}

def parse_un(path: str) -> tuple[list[Entity], list[Relationship]]:
    tree = ET.parse(path)
    root = tree.getroot()
    entities = []
    relationships = []

    for entry in root.findall('.//INDIVIDUAL'):
        uid = entry.findtext('DATAID')
        first = entry.findtext('FIRST_NAME') or ""
        second = entry.findtext('SECOND_NAME') or ""
        third = entry.findtext('THIRD_NAME') or ""
        primary_name = ' '.join(p for p in [first, second, third] if p)

        aliases = []
        for aka in entry.findall('.//ALIAS'):
            parts = [
                aka.findtext('QUALITY'),
                aka.findtext('ALIAS_NAME'),
            ]
            alias = aka.findtext('ALIAS_NAME')
            if alias:
                aliases.append(alias)

        nationality = entry.findtext('.//NATIONALITY/VALUE')
        dob = entry.findtext('.//DATE_OF_BIRTH/VALUE')

        addresses = []
        for addr in entry.findall('.//ADDRESS'):
            parts = [
                addr.findtext('STREET'),
                addr.findtext('CITY'),
                addr.findtext('COUNTRY'),
            ]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)

        entities.append(Entity(
            id=f"un_{uid}",
            entity_type="Person",
            primary_name=primary_name,
            aliases=aliases,
            nationality=nationality,
            dob=dob,
            source="un",
            raw_addresses=addresses,
        ))

    for entry in root.findall('.//ENTITY'):
        uid = entry.findtext('DATAID')
        primary_name = entry.findtext('FIRST_NAME') or ""

        aliases = []
        for aka in entry.findall('.//ALIAS'):
            alias = aka.findtext('ALIAS_NAME')
            if alias:
                aliases.append(alias)

        addresses = []
        for addr in entry.findall('.//ADDRESS'):
            parts = [
                addr.findtext('STREET'),
                addr.findtext('CITY'),
                addr.findtext('COUNTRY'),
            ]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)

        entities.append(Entity(
            id=f"un_{uid}",
            entity_type="Organisation",
            primary_name=primary_name,
            aliases=aliases,
            source="un",
            raw_addresses=addresses,
        ))

    return entities, relationships