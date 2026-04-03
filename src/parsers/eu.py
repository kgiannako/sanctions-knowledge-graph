import xml.etree.ElementTree as ET
from src.models import Entity, Relationship

NS = "http://eu.europa.ec/fpi/fsd/export"

TYPE_MAP = {
    "person": "Person",
    "organisation": "Organisation",
    "vessel": "Vessel"
}

def tag(name: str) -> str:
    return f"{{{NS}}}{name}"

def parse_eu(path: str) -> tuple[list[Entity], list[Relationship]]:
    tree = ET.parse(path)
    root = tree.getroot()
    entities = []
    relationships = []

    for entry in root.findall(tag("sanctionEntity")):
        uid = entry.attrib.get("logicalId")
        un_id = entry.attrib.get("unitedNationId") or None

        subject_type = entry.find(tag("subjectType"))
        etype = subject_type.attrib.get("code", "organisation") if subject_type is not None else "organisation"

        # primary name is the strong=true alias
        primary_name = ""
        aliases = []
        for alias in entry.findall(tag("nameAlias")):
            whole_name = alias.attrib.get("wholeName", "").strip()
            if not whole_name:
                continue
            if alias.attrib.get("strong") == "true" and not primary_name:
                primary_name = whole_name
            else:
                if whole_name:
                    aliases.append(whole_name)

        if not primary_name and aliases:
            primary_name = aliases.pop(0)

        nationality = None
        citizenship = entry.find(tag("citizenship"))
        if citizenship is not None:
            nationality = citizenship.attrib.get("countryIso2Code") or citizenship.attrib.get("country")

        dob = None
        birthdate = entry.find(tag("birthdate"))
        if birthdate is not None:
            dob = birthdate.attrib.get("birthdate")

        imo = None
        for id_el in entry.findall(tag("identification")):
            if "IMO" in id_el.attrib.get("identificationTypeCode", "").upper():
                imo = id_el.attrib.get("number")
                break

        addresses = []
        for addr in entry.findall(tag("address")):
            parts = [
                addr.attrib.get("street"),
                addr.attrib.get("city"),
                addr.attrib.get("countryDescription"),
            ]
            address_str = ', '.join(p for p in parts if p)
            if address_str:
                addresses.append(address_str)

        entities.append(Entity(
            id=f"eu_{uid}",
            entity_type=TYPE_MAP.get(etype.lower(), "Organisation"),
            primary_name=primary_name,
            aliases=aliases,
            nationality=nationality,
            dob=dob,
            imo_number=imo,
            source="eu",
            raw_addresses=addresses,
        ))

    return entities, relationships