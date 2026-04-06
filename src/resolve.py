import re
from src.load_graph import get_driver
from src.search import semantic_search, normalise_org_name

# --- Thresholds ---
SEMANTIC_THRESHOLD = 0.75
COMBINED_THRESHOLD = 0.80
HIGH_SEMANTIC_THRESHOLD = 0.80

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

def extract_year(dob: str) -> str | None:
    if not dob:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', dob)
    return match.group(0) if match else None

def extract_full_date(dob: str) -> str | None:
    if not dob:
        return None
    digits = re.sub(r'\D', '', dob)
    return digits if len(digits) >= 8 else None

def vessel_type_match(type_a: str, type_b: str) -> bool:
    if not type_a or not type_b:
        return False
    a = type_a.lower()
    b = type_b.lower()
    if a == b:
        return True
    return a in b or b in a

def tonnage_match(t_a: str, t_b: str, tolerance: float = 0.05) -> bool:
    if not t_a or not t_b:
        return False
    try:
        ta = float(t_a)
        tb = float(t_b)
        if ta == 0 or tb == 0:
            return False
        return abs(ta - tb) / max(ta, tb) <= tolerance
    except ValueError:
        return False

def attribute_score(
    a: dict,
    b: dict,
    semantic_score: float
) -> tuple[float, list[str], bool]:
    score = 0.0
    reasons = []

    if a.get("type") != b.get("type"):
        return 0.0, ["type mismatch"], True

    entity_type = a.get("type")

    # --- UN reference ID ---
    un_a = a.get("un_ref_id")
    un_b = b.get("un_ref_id")
    if un_a and un_b:
        if un_a == un_b:
            score += 0.45
            reasons.append(f"UN ref ID match: {un_a}")
        else:
            score -= 0.30
            reasons.append(f"UN ref ID mismatch: {un_a} vs {un_b}")

    # --- IMO number ---
    imo_a = a.get("imo_number")
    imo_b = b.get("imo_number")
    if imo_a and imo_b:
        if imo_a == imo_b:
            score += 0.50
            reasons.append(f"IMO match: {imo_a}")
        else:
            return -1.0, [f"IMO mismatch: {imo_a} vs {imo_b}"], True

    # --- Person specific ---
    if entity_type == "Person":
        dob_a = a.get("dob")
        dob_b = b.get("dob")

        if dob_a and dob_b:
            full_a = extract_full_date(dob_a)
            full_b = extract_full_date(dob_b)
            year_a = extract_year(dob_a)
            year_b = extract_year(dob_b)

            if full_a and full_b and full_a == full_b:
                score += 0.20
                reasons.append(f"Full DOB match: {dob_a}")
            elif year_a and year_b:
                if year_a == year_b:
                    score += 0.05
                    reasons.append(f"Birth year match: {year_a}")
                else:
                    score -= 0.25
                    reasons.append(f"Birth year mismatch: {year_a} vs {year_b}")

        nat_a = a.get("nationality") or a.get("country")
        nat_b = b.get("nationality") or b.get("country")
        if nat_a and nat_b and nat_a.upper() == nat_b.upper():
            score += 0.10
            reasons.append(f"Nationality match: {nat_a}")

        # hard reject: borderline semantic with only weak signals
        if semantic_score < HIGH_SEMANTIC_THRESHOLD:
            strong_signals = [r for r in reasons if any(
                s in r for s in ["DOB match", "IMO match", "UN ref"]
            )]
            if not strong_signals and score > 0:
                return 0.0, reasons + ["rejected: borderline semantic with only weak signals"], True

    # --- Vessel specific ---
    if entity_type == "Vessel":
        cs_a = a.get("call_sign")
        cs_b = b.get("call_sign")
        if cs_a and cs_b:
            if cs_a.upper() == cs_b.upper():
                score += 0.30
                reasons.append(f"Call sign match: {cs_a}")
            else:
                score -= 0.20
                reasons.append(f"Call sign mismatch: {cs_a} vs {cs_b}")

        mmsi_a = a.get("mmsi")
        mmsi_b = b.get("mmsi")
        if mmsi_a and mmsi_b:
            if mmsi_a == mmsi_b:
                score += 0.30
                reasons.append(f"MMSI match: {mmsi_a}")
            else:
                score -= 0.20
                reasons.append(f"MMSI mismatch: {mmsi_a} vs {mmsi_b}")

        flag_a = a.get("vessel_flag")
        flag_b = b.get("vessel_flag")
        if flag_a and flag_b:
            if flag_a.upper() == flag_b.upper():
                score += 0.08
                reasons.append(f"Flag match: {flag_a}")
            else:
                score -= 0.10
                reasons.append(f"Flag mismatch: {flag_a} vs {flag_b}")

        if vessel_type_match(a.get("vessel_type"), b.get("vessel_type")):
            score += 0.08
            reasons.append(f"Vessel type match: {a.get('vessel_type')} ~ {b.get('vessel_type')}")

        if tonnage_match(a.get("tonnage"), b.get("tonnage")):
            score += 0.10
            reasons.append(f"Tonnage match: {a.get('tonnage')}")

        owner_a = a.get("vessel_owner")
        owner_b = b.get("vessel_owner")
        if owner_a and owner_b:
            if owner_a.upper() == owner_b.upper():
                score += 0.15
                reasons.append(f"Owner match: {owner_a}")

    # --- Organisation specific ---
    if entity_type == "Organisation":
        country_a = a.get("country")
        country_b = b.get("country")
        if country_a and country_b:
            if country_a.upper() == country_b.upper():
                score += 0.10
                reasons.append(f"Country match: {country_a}")
            else:
                score -= 0.15
                reasons.append(f"Country mismatch: {country_a} vs {country_b}")

        prog_a = set(a.get("programs") or [])
        prog_b = set(b.get("programs") or [])
        shared = prog_a & prog_b
        if shared:
            prog_score = min(len(shared) * 0.05, 0.10)
            score += prog_score
            reasons.append(f"Shared programs: {shared}")

    return score, reasons, False


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
    hard_rejects = 0
    processed = 0
    seen_pairs = set()

    for entity in entities:
        processed += 1
        if processed % 2000 == 0:
            print(f"  Processed {processed}/{len(entities)}...")

        if not entity["name"]:
            continue

        # normalise organisation names to strip common business terms
        query = normalise_org_name(entity["name"]) if entity["type"] == "Organisation" else entity["name"]

        candidates = semantic_search(
            query=query,
            top_k=5,
            entity_type=entity["type"],
            exclude_source=entity["source"]
        )

        for candidate in candidates:
            if candidate["semantic_score"] < SEMANTIC_THRESHOLD:
                continue

            pair_key = tuple(sorted([entity["id"], candidate["id"]]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            details_a = get_entity_details(entity["id"])
            details_b = get_entity_details(candidate["id"])

            attr_score, reasons, hard_reject = attribute_score(
                details_a, details_b, candidate["semantic_score"]
            )

            if hard_reject:
                hard_rejects += 1
                continue

            # require higher semantic confidence if no attribute evidence
            if attr_score == 0.0 and not reasons:
                threshold = 0.95 if entity["type"] == "Organisation" else 0.90
                if candidate["semantic_score"] < threshold:
                    continue

            combined = candidate["semantic_score"] + attr_score

            if combined >= COMBINED_THRESHOLD:
                matches.append({
                    "id_a": entity["id"],
                    "name_a": entity["name"],
                    "source_a": entity["source"],
                    "id_b": candidate["id"],
                    "name_b": candidate["text"],
                    "source_b": candidate["source"],
                    "type": entity["type"],
                    "semantic_score": candidate["semantic_score"],
                    "attribute_score": attr_score,
                    "combined_score": combined,
                    "reasons": reasons,
                })

    print(f"\nResolution complete:")
    print(f"  Pairs evaluated:  {len(seen_pairs)}")
    print(f"  Hard rejects:     {hard_rejects}")
    print(f"  Matches found:    {len(matches)}")

    by_type = {}
    for m in matches:
        by_type[m["type"]] = by_type.get(m["type"], 0) + 1
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count} matches")

    if not dry_run:
        print("\nWriting SAME_AS edges to Neo4j...")
        with driver.session() as session:
            for m in matches:
                session.run("""
                    MATCH (a:Entity {id: $id_a}), (b:Entity {id: $id_b})
                    MERGE (a)-[r:SAME_AS {
                        semantic_score: $semantic_score,
                        attribute_score: $attribute_score,
                        combined_score: $combined_score,
                        reasons: $reasons
                    }]->(b)
                """,
                    id_a=m["id_a"],
                    id_b=m["id_b"],
                    semantic_score=m["semantic_score"],
                    attribute_score=m["attribute_score"],
                    combined_score=m["combined_score"],
                    reasons=m["reasons"],
                )
        print("Done.")

    driver.close()
    return matches


if __name__ == "__main__":
    matches = resolve_entities(dry_run=False)

    print("\n--- Sample matches ---")
    for m in matches[:15]:
        print(f"\n  [{m['type']}] {m['name_a']} [{m['source_a']}]")
        print(f"  → {m['name_b']} [{m['source_b']}]")
        print(f"  semantic: {m['semantic_score']:.3f} | attribute: {m['attribute_score']:.3f} | combined: {m['combined_score']:.3f}")
        print(f"  reasons: {m['reasons']}")