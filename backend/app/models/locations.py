"""Location and facility related database models."""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, Enum, Float
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin
from .enums import BuildingCategory, FacilityCategory, RegionType

if TYPE_CHECKING:
    from .diaries import Diary


class Region(TimestampMixin, BaseModel, table=True):
    """Scenic or campus region."""

    __tablename__ = "regions"

    name: str = Field(index=True, unique=True)
    type: RegionType = Field(sa_column=Column(Enum(RegionType, name="region_type")))
    popularity: int = Field(default=0, ge=0, le=100)
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    description: Optional[str] = None
    city: Optional[str] = Field(default=None, index=True)
    latitude: Optional[float] = Field(default=None, sa_column=Column(Float))
    longitude: Optional[float] = Field(default=None, sa_column=Column(Float))

    buildings: List["Building"] = Relationship(back_populates="region")
    facilities: List["Facility"] = Relationship(back_populates="region")
    diaries: List["Diary"] = Relationship(back_populates="region")


class Building(TimestampMixin, BaseModel, table=True):
    """Building inside a region (scenic spot, teaching building, etc.)."""

    __tablename__ = "buildings"

    region_id: int = Field(foreign_key="regions.id", index=True)
    name: str = Field(index=True)
    category: BuildingCategory = Field(
        sa_column=Column(Enum(BuildingCategory, name="building_category"))
    )
    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))

    region: Region = Relationship(back_populates="buildings")


class Facility(TimestampMixin, BaseModel, table=True):
    """Service facility inside a region (restroom, restaurant, etc.)."""

    __tablename__ = "facilities"

    region_id: int = Field(foreign_key="regions.id", index=True)
    name: str = Field(index=True)
    category: FacilityCategory = Field(
        sa_column=Column(Enum(FacilityCategory, name="facility_category"))
    )
    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))

    region: Region = Relationship(back_populates="facilities")
