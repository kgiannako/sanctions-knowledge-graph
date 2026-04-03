from src.parsers.ofac import parse_ofac
from src.parsers.un import parse_un
from src.parsers.eu import parse_eu

ofac_entities, _ = parse_ofac("data/raw/sdn.xml")
print(f"OFAC - Total: {len(ofac_entities)}")
print(f"  Persons: {len([e for e in ofac_entities if e.entity_type == 'Person'])}")
print(f"  Organisations: {len([e for e in ofac_entities if e.entity_type == 'Organisation'])}")
print(f"  Vessels: {len([e for e in ofac_entities if e.entity_type == 'Vessel'])}")

un_entities, _ = parse_un("data/raw/un_list.xml")
print(f"\nUN - Total: {len(un_entities)}")
print(f"  Persons: {len([e for e in un_entities if e.entity_type == 'Person'])}")
print(f"  Organisations: {len([e for e in un_entities if e.entity_type == 'Organisation'])}")

eu_entities, _ = parse_eu("data/raw/eu_list.xml")
print(f"\nEU - Total: {len(eu_entities)}")
print(f"  Persons: {len([e for e in eu_entities if e.entity_type == 'Person'])}")
print(f"  Organisations: {len([e for e in eu_entities if e.entity_type == 'Organisation'])}")
print(f"  Vessels: {len([e for e in eu_entities if e.entity_type == 'Vessel'])}")

print(f"\nSample EU entity: {eu_entities[0]}")

total = len(ofac_entities) + len(un_entities) + len(eu_entities)
print(f"\nTotal entities across all sources: {total}")