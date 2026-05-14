# Hybrid Tree Search System

A hybrid retrieval system combining LLM-based tree search with value-based prediction using Monte Carlo Tree Search (MCTS) for optimal document retrieval.

## Features

- **Hybrid Search**: Combines speed of value-based methods with depth of LLM-based methods
- **Monte Carlo Tree Search**: Uses MCTS for intelligent node selection and exploration
- **Sentence Transformers**: Leverages pre-trained embeddings for semantic search
- **Configurable Architecture**: Easy to customize weights, models, and search parameters
- **Thread-Safe**: Supports parallel search operations

## Installation

```bash
pip install -r requirements.txt
```

## Requirements

```
sentence-transformers>=2.2.0
torch>=1.9.0
numpy>=1.21.0
tqdm>=4.65.0
google-genai
```

Optional:
- `google-genai` for Gemini API integration

## Architecture

### Components

1. **DocumentTree**: Hierarchical tree structure for documents with chunk support
2. **EmbeddingManager**: Handles embedding generation using sentence transformers
3. **ValueFunction**: Predicts node relevance using embedding similarity
4. **MonteCarloTreeSearch**: MCTS implementation for optimal search
5. **HybridSearchEngine**: Orchestrates all components for hybrid search

### Node Scoring Formula

The system uses a specialized node scoring formula:

```
NodeScore = (1 / sqrt(N + 1)) * sum(ChunkScore(n))
```

Where:
- N = number of chunks in the node
- ChunkScore = relevance score from vector similarity

This rewards nodes with fewer, highly relevant chunks over those with many weakly relevant ones.

## Configuration

```python
from hybrid_tree_search.config import SearchConfig, get_config_for_accuracy, get_config_for_speed

# Default configuration
config = SearchConfig()
```

## Search Modes

```python
from hybrid_tree_search.hybrid_search import SearchMode

options = SearchOptions(mode=SearchMode.HYBRID)
```

## API Reference

### HybridSearchEngine

Main entry point for search operations.

```python
engine = HybridSearchEngine(config=config)
engine.index_tree(tree)           # Index from DocumentTree
response = engine.search(query, options)
stats = engine.get_statistics()
```

### DocumentTree

Hierarchical document structure.

```python
tree = DocumentTree.from_text(text, chunk_size=512, chunk_overlap=50)
tree.add_node(node, parent_id="parent-id")
tree.get_node("node-id")
tree.get_descendants("node-id")
```

### SearchResponse

Results from search operation.

```python
response.query          # Original query
response.results        # List of result dicts
response.search_time    # Time taken
response.metadata       # Additional metadata
```

## License

MIT License