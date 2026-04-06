# sanctions-knowledge-graph

Entity resolution and multi-hop retrieval over public sanctions data using knowledge graphs and semantic search.

## Overview

This project builds a Knowledge Base over public sanctions data from three jurisdictions — OFAC (US), UN, and EU — modelling entities and their relationships as a graph, and layering semantic search on top for fuzzy entity resolution across sources.

The architecture supports AI agent queries requiring multi-hop reasoning: for example, determining whether a vessel is ultimately controlled by a sanctioned individual through a chain of ownership relationships.

## Architecture

```
OFAC SDN (XML) ──┐
UN List (XML)  ──┼──► Parsers ──► Canonical Entity Model ──► Neo4j Graph
EU List (XML)  ──┘                                        ──► FAISS Semantic Index
                                                          ──► Attribute Scorer
                                                          ──► SAME_AS Edge Resolution
                                                          ──► LangGraph Agent (Day 3)
```

## Data Sources

| Source | Jurisdiction | Entities |
|--------|-------------|----------|
| OFAC SDN List | United States | ~18,700 |
| UN Consolidated List | United Nations | ~1,000 |
| EU Financial Sanctions | European Union | ~5,800 |

All sources are publicly available and updated regularly by their respective authorities.

## Stack

- **Neo4j** — graph database for entity and relationship storage
- **Python 3.11** — parsing, normalisation, graph loading
- **Docker** — containerised Neo4j instance
- **sentence-transformers + FAISS** — semantic alias embedding and retrieval
- **LangGraph** — agentic multi-hop query layer *(Day 3)*

## Project Structure

```
sanctions-knowledge-graph/
├── data/
│   └── raw/              # downloaded source XML files (not tracked)
├── src/
│   ├── parsers/
│   │   ├── ofac.py       # OFAC SDN XML parser
│   │   ├── un.py         # UN consolidated list parser
│   │   └── eu.py         # EU financial sanctions parser
│   ├── models.py         # canonical Entity and Relationship dataclasses
│   ├── load_graph.py     # Neo4j loader
│   ├── embed.py          # FAISS index builder
│   ├── search.py         # semantic search with org name normalisation
│   └── resolve.py        # entity resolution and SAME_AS edge writer
├── docker-compose.yml
├── ingest.py             # ingestion orchestration
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+, Anaconda, Docker Desktop

### Installation

```bash
conda create -n sanctions-kg python=3.11 -y
conda activate sanctions-kg
pip install -r requirements.txt
```

### Start Neo4j

```bash
docker compose up -d
```

Neo4j browser at `http://localhost:7474` (neo4j / password123)

### Download data

```bash
curl -L -o data/raw/sdn.xml https://www.treasury.gov/ofac/downloads/sdn.xml
curl -L -o data/raw/un_list.xml https://scsanctions.un.org/resources/xml/en/consolidated.xml
# EU list: download XML manually from https://eeas.europa.eu/topics/sanctions-policy
# Save as data/raw/eu_list.xml
```

### Run pipeline

```bash
python ingest.py          # parse and load entities into Neo4j
python -m src.embed       # build FAISS semantic index
python -m src.resolve     # dry run — inspect matches before writing
# edit resolve.py: dry_run=False, then re-run to write SAME_AS edges
```

## Entity Resolution

The same real-world entity frequently appears across all three lists under different name spellings, transliterations, and formats. The resolution pipeline uses a two-stage approach:

**Stage 1 — Semantic search:** each entity's name is embedded using `all-MiniLM-L6-v2` and queried against a FAISS index of all cross-source entity names and aliases. Candidates above a cosine similarity threshold of 0.75 proceed to stage 2. Organisation names are normalised before embedding to strip common business terms (Bank, Ltd, Group, International etc) that inflate similarity between distinct entities.

**Stage 2 — Attribute scoring:** structured fields provide corroborating or disqualifying evidence:

| Signal | Type | Score |
|--------|------|-------|
| IMO number match | Vessel / Org | +0.50 |
| IMO number mismatch | Vessel / Org | Hard reject |
| UN reference ID match | Organisation | +0.45 |
| Full DOB match | Person | +0.20 |
| Call sign match | Vessel | +0.30 |
| MMSI match | Vessel | +0.30 |
| Birth year match | Person | +0.05 |
| Nationality match | Person | +0.10 |
| Country match | Organisation | +0.10 |
| Country mismatch | Organisation | -0.15 |

Across 25,568 entities and 24,378 evaluated pairs, the pipeline produced 4,076 SAME_AS edges (3,553 persons, 523 organisations) with 307 hard rejects. Score distribution: 53% at combined score 1.0, 28% above 1.0 (IMO or DOB corroboration), 18% in the 0.80–0.95 range. All low-confidence matches were manually audited and confirmed correct.

Pairs with no attribute evidence require a higher semantic threshold (0.95 for organisations, 0.90 for persons) to guard against common-name false positives. Confirmed matches are written as `SAME_AS` edges in Neo4j, storing semantic score, attribute score, combined score, and the evidence reasons on each edge for auditability.

## Production Considerations

- **Batched ingestion:** prototype loads one entity per transaction; production would use `UNWIND` batches of 500–1000 for throughput
- **Multilingual embedding:** `all-MiniLM-L6-v2` is English-primary; a multilingual model would improve coverage of Arabic and Cyrillic name variants
- **Incremental indexing:** currently re-embeds all entities from scratch; production would embed only new or changed entities
- **Vector database:** flat FAISS files work at this scale; production would use a managed vector store (Pinecone, pgvector) for concurrent access and upserts
- **Jurisdiction-agnostic schema:** adding a new sanctions list requires only a new parser module with no downstream changes

## Status

- [x] Data ingestion, canonical model, Neo4j graph
- [x] Semantic embedding, FAISS index, attribute scoring, entity resolution
- [ ] LangGraph agent with graph and semantic retrieval tools
- [ ] Evaluation framework, production narrative, documentation