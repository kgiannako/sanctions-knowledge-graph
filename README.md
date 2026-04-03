# sanctions-knowledge-graph

Entity resolution and multi-hop retrieval over public sanctions data using knowledge graphs and semantic search.

## Overview

This project builds a Knowledge Base over public sanctions data from three jurisdictions — OFAC (US), UN, and EU — modelling entities and their relationships as a graph, and layering semantic search on top for fuzzy entity resolution across sources.

The architecture is designed to support AI agent queries that require multi-hop reasoning: for example, determining whether a vessel is ultimately controlled by a sanctioned individual through a chain of ownership relationships.

## Architecture

```
OFAC SDN (XML) ──┐
UN List (XML)  ──┼──► Parsers ──► Canonical Entity Model ──► Neo4j Graph
EU List (XML)  ──┘                                        ──► FAISS Semantic Index (Day 2)
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
- **sentence-transformers + FAISS** — semantic alias embedding and retrieval *(Day 2)*
- **LangGraph** — agentic multi-hop query layer *(Day 3)*

## Project Structure

```
sanctions-knowledge-graph/
├── data/
│   └── raw/              # downloaded source XML files
├── src/
│   ├── parsers/
│   │   ├── ofac.py       # OFAC SDN XML parser
│   │   ├── un.py         # UN consolidated list parser
│   │   └── eu.py         # EU financial sanctions parser
│   ├── models.py         # canonical Entity and Relationship dataclasses
│   └── load_graph.py     # Neo4j loader
├── docker-compose.yml
├── ingest.py             # orchestration script
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Anaconda
- Docker Desktop

### Installation

```bash
conda create -n sanctions-kg python=3.11 -y
conda activate sanctions-kg
pip install neo4j lxml
```

### Start Neo4j

```bash
docker compose up -d
```

Neo4j browser available at `http://localhost:7474`

| Field | Value |
|-------|-------|
| Username | neo4j |
| Password | password123 |

### Download data

```bash
# OFAC SDN list
curl -L -o data/raw/sdn.xml https://www.treasury.gov/ofac/downloads/sdn.xml

# UN consolidated list
curl -L -o data/raw/un_list.xml https://scsanctions.un.org/resources/xml/en/consolidated.xml

# EU list — download manually from:
# https://eeas.europa.eu/topics/sanctions-policy/8442/consolidated-list-sanctions_en
# Save as data/raw/eu_list.xml
```

### Run ingestion

```bash
python ingest.py
```

Expected output:

```
Parsing sources...
Total entities to load: 25568
Connecting to Neo4j...
Creating constraints...
Loading entities...
Loading relationships...
Done.
```

### Verify in Neo4j browser

```cypher
MATCH (n:Entity) RETURN n.type, count(*) ORDER BY count(*) DESC
```

| Type | Count |
|------|-------|
| Person | ~12,500 |
| Organisation | ~11,600 |
| Vessel | ~1,450 |

## Entity Resolution

The same real-world entity frequently appears across all three lists under different name spellings, transliterations, and formats. For example, a sanctioned individual may appear as `"PUTIN, Vladimir"` in OFAC, `"Vladimir Vladimirovich Putin"` in the UN list, and `"Vladimir Putin"` in the EU list — each with a different internal ID.

Currently each source maintains its own ID namespace (`ofac_*`, `un_*`, `eu_*`). Day 2 introduces semantic embedding of alias fields to identify cross-source matches and draw `SAME_AS` edges between them in the graph, enabling the agent to consolidate information across jurisdictions when answering queries.

## Production Considerations

This prototype loads entities one at a time per transaction. At production scale this would move to batched `UNWIND` transactions of 500–1000 records for throughput. The canonical entity model is jurisdiction-agnostic — adding a new sanctions list requires only a new parser module with no changes to the loader or downstream components. The schema is also designed to accommodate local regulatory and linguistic constraints per market, aligning with a global-plus-local deployment pattern.

## Status

- [x] Day 1 — Data ingestion, canonical model, Neo4j graph
- [ ] Day 2 — Semantic embedding, FAISS index, entity resolution
- [ ] Day 3 — LangGraph agent with graph and semantic retrieval tools
- [ ] Day 4 — Evaluation framework, production narrative, documentation