import json
from src.load_graph import get_driver
from src.search import semantic_search

SEMANTIC_THRESHOLD = 0.75
COMBINED_THRESHOLD = 0.80

def get_entity_details(entity_id: str) -> dict:
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (n:Entity {id: $id})
            RETURN n
        """, id=entity_id)
        record = result.single()
        if record:
            return dict(record["n"])
    driver.close()
    return {}

def attribute_score(a: dict, b: dict) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []

    # must be same entity type
    if a.get("type") != b.get("type"):
        return 0.0, ["type mismatch"]

    entity_type = a.get("type")

    # IMO number — near certain match signal
    imo_a = a.get("imo_number")
    imo_b = b.get("imo_number")
    if imo_a and imo_b:
        if imo_a == imo_b:
            score += 0.50
            reasons.append(f"IMO match: {imo_a}")
        else:
            score -= 0.30
            reasons.append(f"IMO mismatch: {imo_a} vs {imo_b}")

    if entity_type == "Person":
        # DOB exact match
        dob_a = a.get("dob")
        dob_b = b.get("dob")
        if dob_a and dob_b:
            if dob_a == dob_b:
                score += 0.30
                reasons.append(f"DOB match: {dob_a}")
            else:
                score -= 0.20
                reasons.append(f"DOB mismatch: {dob_a} vs {dob_b}")

        # nationality match
        nat_a = a.get("nationality") or a.get("country")
        nat_b = b.get("nationality") or b.get("country")
        if nat_a and nat_b:
            if nat_a.upper() == nat_b.upper():
                score += 0.10
                reasons.append(f"Nationality match: {nat_a}")

    if entity_type == "Vessel":
        # flag state match
        flag_a = a.get("vessel_flag")
        flag_b = b.get("vessel_flag")
        if flag_a and flag_b:
            if flag_a.upper() == flag_b.upper():
                score += 0.10
                reasons.append(f"Flag match: {flag_a}")
            else:
                score -= 0.10
                reasons.append(f"Flag mismatch: {flag_a} vs {flag_b}")

    if entity_type == "Organisation":
        # country match
        country_a = a.get("country")
        country_b = b.get("country")
        if country_a and country_b:
            if country_a.upper() == country_b.upper():
                score += 0.10
                reasons.append(f"Country match: {country_a}")

    return score, reasons

def resolve_entities(dry_run: bool = True):
    driver = get_driver()

    with driver.session() as session:
        result = session.run("""
            MATCH (n:Entity)
            RETURN n.id AS id, n.name AS name, n.type AS type, n.source AS source
        """)
        entities = [dict(r) for r in result]

    print(f"Resolving {len(entities)} entities...")
    matches = []
    processed = 0

    for entity in entities:
        processed += 1
        if processed % 1000 == 0:
            print(f"  Processed {processed}/{len(entities)}...")

        # search for candidates from different sources
        candidates = semantic_search(
            query=entity["name"],
            top_k=5,
            entity_type=entity["type"],
            exclude_source=entity["source"]
        )

        for candidate in candidates:
            if candidate["semantic_score"] < SEMANTIC_THRESHOLD:
                continue

            # avoid duplicate pairs
            pair_key = tuple(sorted([entity["id"], candidate["id"]]))
            if pair_key in {tuple(sorted([m["id_a"], m["id_b"]])) for m in matches}:
                continue

            # get full details for attribute scoring
            details_a = get_entity_details(entity["id"])
            details_b = get_entity_details(candidate["id"])

            attr_score, reasons = attribute_score(details_a, details_b)
            combined = candidate["semantic_score"] + attr_score

            if combined >= COMBINED_THRESHOLD:
                matches.append({
                    "id_a": entity["id"],
                    "name_a": entity["name"],
                    "source_a": entity["source"],
                    "id_b": candidate["id"],
                    "name_b": candidate["name"],
                    "source_b": candidate["source"],
                    "semantic_score": candidate["semantic_score"],
                    "attribute_score": attr_score,
                    "combined_score": combined,
                    "reasons": reasons,
                })

    print(f"Found {len(matches)} matches above threshold")

    if not dry_run:
        print("Writing SAME_AS edges to Neo4j...")
        with driver.session() as session:
            for m in matches:
                session.run("""
                    MATCH (a:Entity {id: $id_a}), (b:Entity {id: $id_b})
                    MERGE (a)-[r:SAME_AS {
                        semantic_score: $semantic_score,
                        attribute_score: $attribute_score,
                        combined_score: $combined_score
                    }]->(b)
                """,
                    id_a=m["id_a"],
                    id_b=m["id_b"],
                    semantic_score=m["semantic_score"],
                    attribute_score=m["attribute_score"],
                    combined_score=m["combined_score"],
                )
        print("Done.")

    driver.close()
    return matches

if __name__ == "__main__":
    # dry run first — inspect matches before writing to graph
    matches = resolve_entities(dry_run=True)

    print("\n--- Sample matches ---")
    for m in matches[:10]:
        print(f"\n  {m['name_a']} [{m['source_a']}]")
        print(f"  → {m['name_b']} [{m['source_b']}]")
        print(f"  semantic: {m['semantic_score']:.3f} | attribute: {m['attribute_score']:.3f} | combined: {m['combined_score']:.3f}")
        print(f"  reasons: {m['reasons']}")