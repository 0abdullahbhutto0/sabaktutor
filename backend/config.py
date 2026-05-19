"""
Configuration Module for Hybrid Tree Search System
===================================================
Handles all configuration parameters for embedding and MCTS components.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class EmbeddingConfig:
    """Configuration for embedding models."""

    model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    batch_size: int = 32
    max_seq_length: int = 512
    device: str = "cpu"
    normalize_embeddings: bool = True
    cache_folder: Optional[str] = None

    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 50
    max_chunk_size: int = 1024

    def __post_init__(self):
        """Validate configuration."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")


@dataclass
class MCTSConfig:
    """Configuration for Monte Carlo Tree Search."""

    max_iterations: int = 75
    max_depth: int = 50
    exploration_constant: float = 1.414
    min_visits: int = 5

    value_weight: float = 0.7
    diversity_weight: float = 0.3

    early_stop_threshold: float = 0.8
    min_results: int = 3
    max_results: int = 20

    parallel_value_searches: int = 4
    rollout_depth: int = 5
    rollout_sampling: str = "best"

    cache_evaluations: bool = True
    cache_ttl: int = 3600

    def __post_init__(self):
        """Validate configuration."""
        if self.exploration_constant <= 0:
            raise ValueError("exploration_constant must be positive")
        if not 0 <= self.value_weight <= 1:
            raise ValueError("value_weight must be between 0 and 1")
        if not 0 <= self.diversity_weight <= 1:
            raise ValueError("diversity_weight must be between 0 and 1")

        total = self.value_weight + self.diversity_weight
        if abs(total - 1.0) > 0.01:
            self.value_weight /= total
            self.diversity_weight /= total


@dataclass
class SearchConfig:
    """Main configuration for the search system."""

    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    mcts: MCTSConfig = field(default_factory=MCTSConfig)

    top_k_chunks: int = 10
    score_aggregation: str = "mean"
    use_square_root_normalization: bool = True

    log_level: str = "INFO"
    enable_progress_bar: bool = True
    max_workers: int = 4

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SearchConfig":
        """Create config from dictionary."""
        embedding_config = EmbeddingConfig(**config_dict.get("embedding", {}))
        mcts_config = MCTSConfig(**config_dict.get("mcts", {}))
        return cls(
            embedding=embedding_config,
            mcts=mcts_config,
            **{k: v for k, v in config_dict.items() if k not in ["embedding", "mcts"]}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "embedding": {
                "model_name": self.embedding.model_name,
                "embedding_dim": self.embedding.embedding_dim,
                "batch_size": self.embedding.batch_size,
                "max_seq_length": self.embedding.max_seq_length,
                "device": self.embedding.device,
                "normalize_embeddings": self.embedding.normalize_embeddings,
                "chunk_size": self.embedding.chunk_size,
                "chunk_overlap": self.embedding.chunk_overlap,
            },
            "mcts": {
                "max_iterations": self.mcts.max_iterations,
                "max_depth": self.mcts.max_depth,
                "exploration_constant": self.mcts.exploration_constant,
                "value_weight": self.mcts.value_weight,
                "diversity_weight": self.mcts.diversity_weight,
                "early_stop_threshold": self.mcts.early_stop_threshold,
            },
            "top_k_chunks": self.top_k_chunks,
            "score_aggregation": self.score_aggregation,
            "log_level": self.log_level,
        }


DEFAULT_CONFIG = SearchConfig()


def get_default_config() -> SearchConfig:
    """Get the default configuration."""
    return DEFAULT_CONFIG