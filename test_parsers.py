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

vessels = [e for e in ofac_entities if e.entity_type == "Vessel"]
with_imo = [e for e in vessels if e.imo_number]
print(f"\nOFAC vessels with IMO: {len(with_imo)} / {len(vessels)}")
print(f"Sample vessel: {with_imo[0] if with_imo else 'none'}")

vessels = [e for e in ofac_entities if e.entity_type == "Vessel"]
with_callsign = [e for e in vessels if e.call_sign]
with_mmsi = [e for e in vessels if e.mmsi]
with_un_ref = [e for e in ofac_entities if e.un_ref_id]

print(f"\nOFAC vessels with call sign: {len(with_callsign)} / {len(vessels)}")
print(f"OFAC vessels with MMSI: {len(with_mmsi)} / {len(vessels)}")
print(f"OFAC entities with UN ref ID: {len(with_un_ref)}")

if with_callsign:
    print(f"Sample call sign: {with_callsign[0].primary_name} — {with_callsign[0].call_sign}")
if with_mmsi:
    print(f"Sample MMSI: {with_mmsi[0].primary_name} — {with_mmsi[0].mmsi}")