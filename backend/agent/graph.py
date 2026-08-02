# backend/agent/graph.py
from langgraph.graph import StateGraph, END, START
from .state import GraphState
from .nodes import rewrite_query, hybrid_retrieve, generate_response

# 1. Initialize the workflow with our GraphState schema
workflow = StateGraph(GraphState)

# 2. Add the asynchronous nodes
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("hybrid_retrieve", hybrid_retrieve)
workflow.add_node("generate_response", generate_response)

# 3. Connect nodes with linear edges
# workflow.add_edge(START, "rewrite_query")
# workflow.add_edge("rewrite_query", "hybrid_retrieve")
workflow.add_edge(START, "hybrid_retrieve")
workflow.add_edge("hybrid_retrieve", "generate_response")
workflow.add_edge("generate_response", END)

# 4. Compile into a runnable graph app
graph_app = workflow.compile()
