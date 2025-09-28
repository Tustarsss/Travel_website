"""Repository abstractions for data persistence."""

from .graph import GraphRepository
from .regions import RegionRepository

__all__ = ["RegionRepository", "GraphRepository"]
