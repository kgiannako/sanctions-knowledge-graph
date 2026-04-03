from neo4j import GraphDatabase
from src.models import Entity, Relationship

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def get_driver():
    return GraphDatabase.driver(URI, auth=AUTH)

def create_constraints(driver):
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT entity_id IF NOT EXISTS
            FOR (n:Entity) REQUIRE n.id IS UNIQUE
        """)

def load_entities(driver, entities: list[Entity]):
    with driver.session() as session:
        for e in entities:
            session.run("""
                MERGE (n:Entity {id: $id})
                SET n.type = $type,
                    n.name = $name,
                    n.aliases = $aliases,
                    n.nationality = $nationality,
                    n.dob = $dob,
                    n.imo_number = $imo_number,
                    n.source = $source,
                    n.programs = $programs,
                    n.addresses = $addresses,
                    n.country = $country,
                    n.vessel_flag = $vessel_flag,
                    n.vessel_type = $vessel_type,
                    n.vessel_owner = $vessel_owner,
                    n.tonnage = $tonnage
            """,
                id=e.id,
                type=e.entity_type,
                name=e.primary_name,
                aliases=e.aliases,
                nationality=e.nationality,
                dob=e.dob,
                imo_number=e.imo_number,
                source=e.source,
                programs=e.programs,
                addresses=e.raw_addresses,
                country=e.country,
                vessel_flag=e.vessel_flag,
                vessel_type=e.vessel_type,
                vessel_owner=e.vessel_owner,
                tonnage=e.tonnage,
            )

def load_relationships(driver, relationships: list[Relationship]):
    with driver.session() as session:
        for r in relationships:
            session.run(f"""
                MATCH (a:Entity {{id: $src}}), (b:Entity {{id: $tgt}})
                MERGE (a)-[:{r.rel_type}]->(b)
            """,
                src=r.source_id,
                tgt=r.target_id,
            )