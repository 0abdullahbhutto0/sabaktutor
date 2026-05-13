#!/usr/bin/env python3
"""
Hybrid Tree Search - Main Entry Point
======================================
Search your document tree with MCTS + LLM hybrid approach.

Usage:
    python main.py tree.json "your query"
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from google import genai

from hybrid_tree_search import (
    HybridSearchEngine,
    SearchOptions,
    SearchMode,
    DocumentTree,
    TreeNode,
    Chunk,
)


def load_tree_from_json(filepath: str) -> DocumentTree:
    """
    Load document tree from JSON file.

    Supports formats:
    1. Simple document list:
       [{"id": "d1", "title": "...", "content": "..."}]

    2. Hierarchical tree (like your format):
       [{"node_id": "0001", "title": "...", "text": "...", "summary": "...", "nodes": [...]}]
    """
    with open(filepath, 'r',encoding='utf-8') as f:
        data = json.load(f)

    tree = DocumentTree()

    def process_nodes(node_data_list: List[Dict], parent_node_id: Optional[str] = None):
        for node_data in node_data_list:
            # Get node ID - use node_id or generate one
            node_id = node_data.get("node_id") or node_data.get("id") or f"node_{len(tree.nodes)}"

           
            content = node_data.get("text") or node_data.get("content", "")

           
            title = node_data.get("title", "")

            summary = node_data.get("summary", "")

            
            node = TreeNode(
                node_type="document",
                content=content,
                title=title,
                metadata={
                    "node_id": node_id,
                    "summary": summary,
                    "text": content,
                    "start_index": node_data.get("start_index"),
                    "end_index": node_data.get("end_index"),
                },
            )

            # Add chunks from text
            if content:
                chunk = Chunk(
                    content=content,
                    start_char=0,
                    end_char=len(content),
                )
                node.add_chunk(chunk)

            # Add to tree
            if parent_node_id:
                tree.add_node(node, parent_id=parent_node_id)
            else:
                tree.add_node(node)

            # Process children
            child_nodes = node_data.get("nodes", [])
            if child_nodes:
                process_nodes(child_nodes, parent_node_id=node.id)

    # Handle both list and dict formats
    if isinstance(data, list):
        process_nodes(data)
    elif isinstance(data, dict) and "nodes" in data:
        process_nodes(data["nodes"])
    elif isinstance(data, dict):
        process_nodes([data])

    return tree


def search(tree: DocumentTree, query: str, mode: str , max_results: int ) -> Dict[str, Any]:
    """
    Search the document tree.

    Args:
        tree: DocumentTree to search
        query: Search query
        mode: "hybrid", "value_only", "mcts_only", "llm_only"
        max_results: Maximum results

    Returns:
        Search results dictionary
    """
    engine = HybridSearchEngine()
    engine.index_tree(tree)

    mode_map = {
        "hybrid": SearchMode.HYBRID,
        "value_only": SearchMode.VALUE_ONLY,
        "mcts_only": SearchMode.MCTS_ONLY,
        "llm_only": SearchMode.LLM_ONLY,
    }

    options = SearchOptions(
        mode=mode_map.get(mode, SearchMode.HYBRID),
        max_results=max_results,
        
    )

    response = engine.search(query, options)
    
    return response.to_dict()


def main():
    print("=" * 70)
    print("Hybrid Tree Search with MCTS + LLM")
    print("=" * 70)

  
    filepath = 'cs_9.json'

    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}")
        return

    query='what is views in database'

    if not query:
        print("Error: No query provided")
        return

    # Get mode
    mode = "hybrid"
   

    # Load tree
    print(f"\nLoading tree from: {filepath}")
    tree = load_tree_from_json(filepath)
    print(f"Tree loaded: {tree.get_node_count()} nodes")

    # Perform search
    print(f"\nSearching for: '{query}'")
    print(f"Mode: {mode}")
    print("-" * 70)

    results = search(tree, query, mode=mode, max_results=5)

    # Print results
    print(f"\nFound {len(results['results'])} results in {results['search_time']:.3f}s\n")

  
    gemini_key = ''

    print("\n" + "=" * 70)
    print("GEMINI RESPONSE (Streaming)")
    print("=" * 70 + "\n")

    try:
        client = genai.Client(api_key=gemini_key)

        context_text = "\n\n".join(
            [
                f"Source: {r.get('title')}\nContent: {r.get('content')}"
                for r in results["results"]
            ]
        )

        prompt = f"""
You are a  TEACHER.

You must teach  using ONLY the given context.

If the context is incomplete, explicitly say so.


Context is from a textbook and may be partial.

Context:
{context_text}

Question:
{query}

Answer in this format:
1. Simple Definition
2. Explanation
3. Example (if available)
"""

        stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        for chunk in stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)

        print("\n")

    except Exception as e:
        print(f"\n[!] Gemini Error: {e}")


if __name__ == "__main__":
    main()