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
