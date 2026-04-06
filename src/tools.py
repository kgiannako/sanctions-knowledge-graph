from src.load_graph import get_driver
from src.search import semantic_search

def graph_lookup(entity_id: str) -> dict:
    """
    Fetch full entity details from Neo4j including all SAME_AS linked entities
    across sources and any ownership/association relationships.
    """
    driver = get_driver()
    result = {}

    with driver.session() as session:
        # fetch the entity itself
        record = session.run("""
            MATCH (n:Entity {id: $id})
            RETURN n
        """, id=entity_id).single()

        if not record:
            return {"error": f"Entity {entity_id} not found"}

        node = dict(record["n"])
        result["entity"] = node

        # fetch SAME_AS linked entities across sources
        same_as = session.run("""
            MATCH (n:Entity {id: $id})-[r:SAME_AS]-(m:Entity)
            RETURN m, r.combined_score AS score, r.reasons AS reasons
            ORDER BY r.combined_score DESC
        """, id=entity_id).data()

        result["same_as"] = [
            {
                "id": r["m"]["id"],
                "name": r["m"]["name"],
                "source": r["m"]["source"],
                "type": r["m"]["type"],
                "combined_score": r["score"],
                "reasons": r["reasons"],
            }
            for r in same_as
        ]

        # fetch ownership/association relationships
        relationships = session.run("""
            MATCH (n:Entity {id: $id})-[r]->(m:Entity)
            WHERE type(r) <> 'SAME_AS'
            RETURN type(r) AS rel_type, m.id AS target_id,
                   m.name AS target_name, m.type AS target_type,
                   m.source AS target_source
        """, id=entity_id).data()

        result["relationships"] = relationships

    driver.close()
    return result


def search_entities(query: str, entity_type: str = None, top_k: int = 5) -> list[dict]:
    """
    Search for entities by name using semantic similarity.
    entity_type can be 'Person', 'Organisation', or 'Vessel'.
    Returns top_k candidates with scores.
    """
    results = semantic_search(
        query=query,
        top_k=top_k,
        entity_type=entity_type,
    )

    return [
        {
            "id": r["id"],
            "name": r["text"],
            "type": r["type"],
            "source": r["source"],
            "score": r["semantic_score"],
        }
        for r in results
    ]


def get_consolidated_profile(entity_id: str) -> dict:
    """
    Returns a consolidated profile of an entity by merging information
    from the entity itself and all its SAME_AS linked entities.
    Useful for getting a complete picture across all three sanctions lists.
    """
    profile = graph_lookup(entity_id)

    if "error" in profile:
        return profile

    entity = profile["entity"]
    same_as = profile["same_as"]

    # consolidate fields across linked entities
    all_aliases = list(entity.get("aliases") or [])
    all_programs = list(entity.get("programs") or [])
    all_addresses = list(entity.get("addresses") or [])
    sources = [entity.get("source")]

    for linked in same_as:
        linked_details = graph_lookup(linked["id"])
        if "entity" in linked_details:
            e = linked_details["entity"]
            all_aliases += [a for a in (e.get("aliases") or []) if a not in all_aliases]
            all_programs += [p for p in (e.get("programs") or []) if p not in all_programs]
            all_addresses += [a for a in (e.get("addresses") or []) if a not in all_addresses]
            sources.append(e.get("source"))

    return {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "type": entity.get("type"),
        "sources": list(set(sources)),
        "aliases": all_aliases,
        "programs": all_programs,
        "addresses": all_addresses,
        "nationality": entity.get("nationality"),
        "dob": entity.get("dob"),
        "imo_number": entity.get("imo_number"),
        "vessel_flag": entity.get("vessel_flag"),
        "vessel_type": entity.get("vessel_type"),
        "same_as_count": len(same_as),
        "same_as": same_as,
        "relationships": profile.get("relationships", []),
    }


if __name__ == "__main__":
    print("--- Test: search for Bin Laden ---")
    results = search_entities("Bin Laden", entity_type="Person", top_k=3)
    for r in results:
        print(f"  [{r['source']}] {r['name']} (score: {r['score']:.3f}) id: {r['id']}")

    if results:
        top_id = results[0]["id"]
        print(f"\n--- Test: graph lookup for {top_id} ---")
        profile = get_consolidated_profile(top_id)
        print(f"  Name: {profile['name']}")
        print(f"  Sources: {profile['sources']}")
        print(f"  SAME_AS links: {profile['same_as_count']}")
        print(f"  Aliases: {profile['aliases'][:5]}")
        print(f"  Programs: {profile['programs']}")

    print("\n--- Test: search for Al Qaeda ---")
    results = search_entities("Al Qaeda", entity_type="Organisation", top_k=3)
    for r in results:
        print(f"  [{r['source']}] {r['name']} (score: {r['score']:.3f}) id: {r['id']}")