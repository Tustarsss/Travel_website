"""Graph related models for routing."""

from typing import List, Optional

from sqlalchemy import JSON, Boolean, Column, Float
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin
from .enums import TransportMode


class GraphNode(TimestampMixin, BaseModel, table=True):
    """A navigable node within a region."""

    __tablename__ = "graph_nodes"

    region_id: int = Field(foreign_key="regions.id", index=True)
    name: Optional[str] = Field(default=None)
    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))
    building_id: Optional[int] = Field(default=None, foreign_key="buildings.id")
    facility_id: Optional[int] = Field(default=None, foreign_key="facilities.id")
    is_virtual: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, default=False))

    outgoing_edges: List["GraphEdge"] = Relationship(
        sa_relationship=relationship(
            "GraphEdge",
            primaryjoin="GraphNode.id == GraphEdge.start_node_id",
            foreign_keys="[GraphEdge.start_node_id]",
            cascade="all, delete-orphan",
            back_populates="start_node",
        )
    )
    incoming_edges: List["GraphEdge"] = Relationship(
        sa_relationship=relationship(
            "GraphEdge",
            primaryjoin="GraphNode.id == GraphEdge.end_node_id",
            foreign_keys="[GraphEdge.end_node_id]",
            cascade="all, delete-orphan",
            back_populates="end_node",
        )
    )


class GraphEdge(TimestampMixin, BaseModel, table=True):
    """Directed weighted edge between nodes."""

    __tablename__ = "graph_edges"

    region_id: int = Field(foreign_key="regions.id", index=True)
    start_node_id: int = Field(foreign_key="graph_nodes.id", index=True)
    end_node_id: int = Field(foreign_key="graph_nodes.id", index=True)
    distance: float = Field(gt=0)
    ideal_speed: float = Field(gt=0)
    congestion: float = Field(gt=0, le=1)
    transport_modes: List[TransportMode] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )

    start_node: GraphNode = Relationship(
        sa_relationship=relationship(
            "GraphNode",
            primaryjoin="GraphEdge.start_node_id == GraphNode.id",
            foreign_keys="[GraphEdge.start_node_id]",
            back_populates="outgoing_edges",
            lazy="joined",
        )
    )
    end_node: GraphNode = Relationship(
        sa_relationship=relationship(
            "GraphNode",
            primaryjoin="GraphEdge.end_node_id == GraphNode.id",
            foreign_keys="[GraphEdge.end_node_id]",
            back_populates="incoming_edges",
            lazy="joined",
        )
    )
