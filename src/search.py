import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = "data/faiss.index"
MAP_PATH = "data/id_map.json"

_model = None
_index = None
_id_map = None

STRIP_TERMS = {
    'bank', 'ltd', 'llc', 'plc', 'inc', 'corp', 'corporation',
    'company', 'co', 'group', 'holding', 'holdings', 'international',
    'trading', 'import', 'export', 'islamic', 'national', 'general',
    'the', 'of', 'and', 'for', 'al', 'el'
}

def normalise_org_name(name: str) -> str:
    if not name:
        return name
    tokens = name.lower().split()
    filtered = [t for t in tokens if t.strip('.,') not in STRIP_TERMS]
    return ' '.join(filtered) if filtered else name.lower()

def _load():
    global _model, _index, _id_map
    if _model is None:
        print("Loading model...")
        _model = SentenceTransformer(MODEL_NAME)
    if _index is None:
        print("Loading FAISS index...")
        _index = faiss.read_index(INDEX_PATH)
    if _id_map is None:
        print("Loading ID map...")
        with open(MAP_PATH, "r", encoding="utf-8") as f:
            _id_map = json.load(f)

def semantic_search(
    query: str,
    top_k: int = 20,
    entity_type: str = None,
    exclude_source: str = None
) -> list[dict]:
    _load()

    query_vec = _model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec).astype("float32")

    search_k = min(top_k * 10, len(_id_map))
    scores, indices = _index.search(query_vec, search_k)

    results = []
    seen_ids = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = _id_map[idx]

        if entity_type and entry["type"] != entity_type:
            continue

        if exclude_source and entry["source"] == exclude_source:
            continue

        if entry["id"] in seen_ids:
            continue
        seen_ids.add(entry["id"])

        results.append({
            "id": entry["id"],
            "text": entry["text"],
            "type": entry["type"],
            "source": entry["source"],
            "is_primary": entry["is_primary"],
            "semantic_score": float(score)
        })

        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    queries = [
        ("Bin Laden", "Person"),
        ("Al Qaeda", "Organisation"),
        ("EBANO", "Vessel"),
    ]

    for query, etype in queries:
        print(f"\n--- Query: '{query}' (type: {etype}) ---")
        results = semantic_search(query, top_k=5, entity_type=etype)
        for r in results:
            print(f"  [{r['source']}] {r['text']} (score: {r['semantic_score']:.3f})")