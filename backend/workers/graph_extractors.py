# backend/workers/graph_extractor.py
import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_neo4j import LLMGraphTransformer
from services.neo4j_client import get_graph_client

# 1. Initialize the reasoning LLM (Requires strong structured output capabilities)
llm_extraction = ChatOpenAI(model="gpt-4o", temperature=0)

# 2. Configure the LLM Graph Transformer
# We constrain the AI to a strict financial schema to maintain database integrity
graph_transformer = LLMGraphTransformer(
    llm=llm_extraction,
    allowed_nodes=[
        "Company", "Subsidiary", "Executive", 
        "RiskFactor", "RevenueStream", "Competitor"
    ],
    allowed_relationships=[
        "OWNS", "MANAGED_BY", "FACES_RISK", 
        "GENERATES_REVENUE", "COMPETES_WITH"
    ],
    node_properties=True, # Allows extraction of properties like "Name" or "Amount"
    relationship_properties=True
)

async def extract_and_store_graph_entities(documents: List[Document]):
    """
    Asynchronously extracts nodes and relationships from SEC 10-K chunks 
    and inserts them into the Neo4j database.
    """
    print(f"---GRAPH INGESTION: Extracting entities from {len(documents)} chunks---")

    # 3. Asynchronously convert text documents into GraphDocuments
    # This prevents blocking the main event loop while waiting on the LLM
    try:
        graph_documents = await graph_transformer.aconvert_to_graph_documents(documents)

        # 4. Store in Neo4j
        # Since add_graph_documents is synchronous in LangChain, we wrap it
        # in asyncio.to_thread to maintain the non-blocking architecture
        graph = get_graph_client()
        await asyncio.to_thread(graph.add_graph_documents, graph_documents)

        # Refresh the schema so the LangGraph agent sees the new structure
        await asyncio.to_thread(graph.refresh_schema)

        print(f"---GRAPH INGESTION COMPLETE: Stored {len(graph_documents)} graph documents---")

    except Exception as e:
        print(f"---GRAPH INGESTION ERROR: {str(e)}---")
