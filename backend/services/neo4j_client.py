# backend/services/neo4j_client.py
import os
from langchain_neo4j import Neo4jGraph

# 1. Environment Variables for Neo4j
# If using Neo4j Aura (cloud), neo4j+s:// is the recommended secure protocol
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# 2. Initialize the Graph Connection
# We set refresh_schema=True so the agent always knows the latest graph structure
neo4j_graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    refresh_schema=True
)

def get_graph_client():
    """Returns the singleton graph client."""
    return neo4j_graph

def get_graph_context(entities: list[str]) -> str:
    """Finds relationships connected to extracted entities."""
    if not entities:
        return ""

    query = """
    MATCH (e)-[r]->(target)
    WHERE any(entity IN $entities WHERE toLower(coalesce(e.id, '')) CONTAINS toLower(entity))
       OR any(entity IN $entities WHERE toLower(coalesce(target.id, '')) CONTAINS toLower(entity))
    RETURN e.id AS source, type(r) AS rel, target.id AS target
    LIMIT 25
    """
    result = neo4j_graph.query(query, params={"entities": entities})
    if not result:
        print("⚠️ Cypher query executed but found 0 matches in the graph.")
    facts = [f"{record['source']} -> {record['rel']} -> {record['target']}" for record in result]
    return "\n".join(facts)
