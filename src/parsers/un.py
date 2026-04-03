import xml.etree.ElementTree as ET
from src.models import Entity, Relationship

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
        for aka in entry.findall('INDIVIDUAL_ALIAS'):
            alias = aka.findtext('ALIAS_NAME')
            if alias:
                aliases.append(alias)

        nationality = entry.findtext('.//NATIONALITY/VALUE')
        dob = entry.findtext('.//INDIVIDUAL_DATE_OF_BIRTH/VALUE')

        addresses = []
        country = None
        for addr in entry.findall('INDIVIDUAL_ADDRESS'):
            country_val = addr.findtext('COUNTRY')
            note = addr.findtext('NOTE')
            parts = [country_val, note]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)
            if not country and country_val:
                country = country_val

        entities.append(Entity(
            id=f"un_{uid}",
            entity_type="Person",
            primary_name=primary_name,
            aliases=aliases,
            nationality=nationality,
            dob=dob,
            source="un",
            raw_addresses=addresses,
            country=country,
        ))

    for entry in root.findall('.//ENTITY'):
        uid = entry.findtext('DATAID')
        primary_name = entry.findtext('FIRST_NAME') or ""

        aliases = []
        for aka in entry.findall('ENTITY_ALIAS'):
            alias = aka.findtext('ALIAS_NAME')
            if alias:
                aliases.append(alias)

        addresses = []
        country = None
        for addr in entry.findall('ENTITY_ADDRESS'):
            country_val = addr.findtext('COUNTRY')
            state = addr.findtext('STATE_PROVINCE')
            parts = [state, country_val]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)
            if not country and country_val:
                country = country_val

        entities.append(Entity(
            id=f"un_{uid}",
            entity_type="Organisation",
            primary_name=primary_name,
            aliases=aliases,
            source="un",
            raw_addresses=addresses,
            country=country,
        ))

    return entities, relationships