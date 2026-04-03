from src.parsers.ofac import parse_ofac
from src.parsers.un import parse_un
from src.parsers.eu import parse_eu
from src.load_graph import get_driver, create_constraints, load_entities, load_relationships

print("Parsing sources...")
ofac_entities, ofac_rels = parse_ofac("data/raw/sdn.xml")
un_entities, un_rels = parse_un("data/raw/un_list.xml")
eu_entities, eu_rels = parse_eu("data/raw/eu_list.xml")

all_entities = ofac_entities + un_entities + eu_entities
all_rels = ofac_rels + un_rels + eu_rels
print(f"Total entities to load: {len(all_entities)}")

print("Connecting to Neo4j...")
driver = get_driver()

print("Creating constraints...")
create_constraints(driver)

print("Loading entities...")
load_entities(driver, all_entities)

print("Loading relationships...")
load_relationships(driver, all_rels)

driver.close()
print("Done.")