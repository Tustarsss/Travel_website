"""Enumerations shared across models."""

from __future__ import annotations

from enum import Enum


class RegionType(str, Enum):
    SCENIC = "scenic"
    CAMPUS = "campus"


class BuildingCategory(str, Enum):
    SCENIC_SPOT = "scenic_spot"
    TEACHING_BUILDING = "teaching_building"
    OFFICE = "office"
    DORMITORY = "dormitory"
    MUSEUM = "museum"
    LIBRARY = "library"
    OTHER = "other"


class FacilityCategory(str, Enum):
    RESTROOM = "restroom"
    RESTAURANT = "restaurant"
    SHOP = "shop"
    SUPERMARKET = "supermarket"
    CAFE = "cafe"
    ATM = "atm"
    MEDICAL = "medical"
    PARKING = "parking"
    INFORMATION = "information"
    SERVICE = "service"


class TransportMode(str, Enum):
    WALK = "walk"
    BIKE = "bike"
    ELECTRIC_CART = "electric_cart"


class DiaryMediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class DiaryStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
