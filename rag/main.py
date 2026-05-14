"""
Hybrid Tree Search - Main Entry Point
======================================
Search your document tree with MCTS + LLM hybrid approach.

Usage:
    python -m main 
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
# from google import genai

from hybrid_tree_search import (
    HybridSearchEngine,
    SearchOptions,
    DocumentTree,
    TreeNode,
    Chunk,
)


def load_tree_from_json(filepath: str) -> DocumentTree:
    """
    Load document tree from JSON file.

    1. Hierarchical tree (like your format):
       [{"node_id": "0001", "title": "...", "text": "...", "summary": "...", "nodes": [...]}]
    """
    with open(filepath, 'r',encoding='utf-8') as f:
        data = json.load(f)

    tree = DocumentTree()

    def process_nodes(node_data_list: List[Dict], parent_node_id: Optional[str] = None):
        for node_data in node_data_list:
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
            if content:
                chunk = Chunk(
                    content=content,
                )
                node.add_chunk(chunk)
            if parent_node_id:
                tree.add_node(node, parent_id=parent_node_id)
            else:
                tree.add_node(node)

            # Process children
            child_nodes = node_data.get("nodes", [])
            if child_nodes:
                process_nodes(child_nodes, parent_node_id=node.id)

    if isinstance(data, list):
        process_nodes(data)
    elif isinstance(data, dict) and "nodes" in data:
        process_nodes(data["nodes"])
    elif isinstance(data, dict):
        process_nodes([data])

    return tree


def search(tree: DocumentTree, query: str , max_results: int ) -> Dict[str, Any]:
    """
    Search the document tree.

    Args:
        tree: DocumentTree to search
        query: Search query
        max_results: Maximum results

    Returns:
        Search results dictionary
    """
    engine = HybridSearchEngine()
    engine.index_tree(tree)

    options = SearchOptions(
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

    print(f"\nLoading tree from: {filepath}")
    tree = load_tree_from_json(filepath)
    print(f"Tree loaded: {tree.get_node_count()} nodes")

    print(f"\nSearching for: '{query}'")
    print("-" * 70)

    results = search(tree, query, max_results=3)

    # print(f"\nFound {len(results['results'])} results in {results['search_time']:.3f}s\n")
    # for i, result in enumerate(results["results"]):
    #     print(f"result# {i+1}: score {result['score']}")
    #     print(f"title: {result['title']}")
    #     print(f"content: {result['content'][:300]}")
    #     print()
  
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