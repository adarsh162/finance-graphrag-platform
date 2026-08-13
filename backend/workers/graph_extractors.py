# backend/workers/graph_extractor.py
import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
# from langchain_neo4j import LLMGraphTransformer
from langchain_experimental.graph_transformers import LLMGraphTransformer
from services.neo4j_client import get_graph_client
from agent.nodes import get_llm

# 1. Initialize the reasoning LLM (Requires strong structured output capabilities)
llm_extraction = get_llm(model_type="fast", temperature=0)

# 2. Configure the LLM Graph Transformer
# We constrain the AI to a strict financial schema to maintain database integrity
allowed_nodes = [
    "Company", 
    "Subsidiary", 
    "Product", 
    "RevenueStream", 
    "RiskFactor",
    "Region",       # Added based on your previous graph
    "Component",    # Added
    "Currency",     # Added
    "Division"      # Added
]
# 2. Define the strict relationship paths (Every source and target MUST be in the list above)
allowed_relationships = [
    ("Company", "HAS_SUBSIDIARY", "Subsidiary"),
    ("Subsidiary", "OPERATES_IN", "RevenueStream"),
    ("Company", "OPERATES_IN", "Region"),
    ("Company", "OPERATES", "Division"),
    ("Company", "USES", "Component"),
    ("Company", "EXPOSED_TO", "Currency"),
    ("Product", "GENERATES", "RevenueStream"),
    ("Company", "FACED_WITH", "RiskFactor")
]
graph_transformer = LLMGraphTransformer(
    llm=llm_extraction,
    # allowed_nodes=allowed_nodes,
    # allowed_relationships=allowed_relationships,
    # node_properties=True, # Allows extraction of properties like "Name" or "Amount"
    relationship_properties=True
)

async def extract_and_store_graph_entities(documents, document_id: str):
    try:
        print("✂️ Splitting document into smaller chunks for graph extraction...")
        # 1. Chunk documents so the LLM isn't overwhelmed by large pages
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
        chunks = text_splitter.split_documents(documents)
        
        # Limit to the first 25-30 chunks to prevent rate-limit bottlenecks during testing
        for chunk in chunks:
            chunk.metadata["source"] = document_id
            chunk.metadata["document_id"] = document_id
        chunks_to_process = chunks[:30]
        print(f"📄 Processing {len(chunks_to_process)} chunks for Neo4j entity extraction...")

        # 2. Define schema constraints to guide the extraction

        llm_transformer = LLMGraphTransformer(
            llm=llm_extraction,
            # allowed_nodes=allowed_nodes,
            # allowed_relationships=allowed_relationships,
            # node_properties=True,
            # relationship_properties=True,
            ignore_tool_usage=False
        )
        # 3. Transform chunks to graph documents
        graph_documents = await llm_transformer.aconvert_to_graph_documents(chunks_to_process)

        # 4. Store in Neo4j
        graph_client = get_graph_client()
        graph_client.add_graph_documents(graph_documents, include_source=True)
        print(f"✅ Extracted {len(graph_documents)} graph sub-structures into Neo4j!")

    except Exception as e:
        print(f"---GRAPH INGESTION ERROR: {str(e)}---")
