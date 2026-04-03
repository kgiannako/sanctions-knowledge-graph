import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.load_graph import get_driver

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = "data/faiss.index"
MAP_PATH = "data/id_map.json"

def build_index():
    print("Loading model...")
    model = SentenceTransformer(MODEL_NAME)

    print("Fetching entities from Neo4j...")
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (n:Entity)
            RETURN n.id AS id, n.name AS name, n.aliases AS aliases, 
                   n.type AS type, n.source AS source
        """)
        records = [dict(r) for r in result]
    driver.close()

    print(f"Building strings to embed for {len(records)} entities...")
    strings = []
    id_map = []

    for r in records:
        name = r["name"] or ""
        aliases = r["aliases"] or []
        entity_id = r["id"]
        entity_type = r["type"]
        source = r["source"]

        if name:
            strings.append(name)
            id_map.append({
                "id": entity_id,
                "text": name,
                "type": entity_type,
                "source": source,
                "is_primary": True
            })

        for alias in aliases:
            if alias and alias != name:
                strings.append(alias)
                id_map.append({
                    "id": entity_id,
                    "text": alias,
                    "type": entity_type,
                    "source": source,
                    "is_primary": False
                })

    print(f"Embedding {len(strings)} strings...")
    embeddings = model.encode(
        strings,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    embeddings = np.array(embeddings).astype("float32")

    print("Building FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    print(f"Saving index to {INDEX_PATH}...")
    faiss.write_index(index, INDEX_PATH)

    print(f"Saving ID map to {MAP_PATH}...")
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False)

    print(f"Done. Index contains {index.ntotal} vectors.")
    print(f"\n--- Index summary ---")
    print(f"Total entities:      {len(records)}")
    print(f"Total strings:       {len(strings)}")
    print(f"  Primary names:     {sum(1 for m in id_map if m['is_primary'])}")
    print(f"  Aliases:           {sum(1 for m in id_map if not m['is_primary'])}")
    print(f"Vectors per entity:  {len(strings)/len(records):.1f} avg")
    print(f"Embedding dim:       {dim}")
    print(f"Index size:          {index.ntotal} vectors")
    print(f"Sources:")
    for src in ['ofac', 'un', 'eu']:
        count = sum(1 for m in id_map if m['source'] == src)
        print(f"  {src}:             {count} vectors")
    return index, id_map

if __name__ == "__main__":
    build_index()