from typing import TypedDict, List
from langchain_core.documents import Document

class GraphState(TypedDict):
    """
    Represents the state of the Dynamic Finance GraphRAG pipeline.
    """
    original_question: str
    optimized_query: str
    documents: List[Document]
    generation: str
    revision_count: int
