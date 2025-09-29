"""Map data crawling utilities for real-world locations."""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from app.models.enums import BuildingCategory, FacilityCategory, RegionType, TransportMode

try:
    import osmnx as ox
    import networkx as nx
    from shapely.geometry import Point, Polygon
    HAS_OSMNX = True
except ImportError:
    HAS_OSMNX = False

# Mapping from OSM amenity tags to our facility categories
OSM_FACILITY_MAPPING = {
    "restaurant": FacilityCategory.RESTAURANT,
    "cafe": FacilityCategory.CAFE,
    "fast_food": FacilityCategory.RESTAURANT,
    "bar": FacilityCategory.RESTAURANT,
    "pub": FacilityCategory.RESTAURANT,
    "toilets": FacilityCategory.RESTROOM,
    "hospital": FacilityCategory.MEDICAL,
    "pharmacy": FacilityCategory.MEDICAL,
    "clinic": FacilityCategory.MEDICAL,
    "parking": FacilityCategory.PARKING,
    "bicycle_parking": FacilityCategory.PARKING,
    "car_rental": FacilityCategory.PARKING,
    "shop": FacilityCategory.SHOP,
    "supermarket": FacilityCategory.SUPERMARKET,
    "convenience": FacilityCategory.SHOP,
    "kiosk": FacilityCategory.SHOP,
    "mall": FacilityCategory.SHOP,
    "marketplace": FacilityCategory.SHOP,
    "bank": FacilityCategory.ATM,
    "atm": FacilityCategory.ATM,
    "library": FacilityCategory.SERVICE,  # Use SERVICE as default for library
    "museum": FacilityCategory.SERVICE,  # Use SERVICE as default for museum
    "theatre": FacilityCategory.SERVICE,  # Use SERVICE as default
    "cinema": FacilityCategory.SERVICE,  # Use SERVICE as default
    "fitness_centre": FacilityCategory.SERVICE,  # Use SERVICE as default
    "gym": FacilityCategory.SERVICE,  # Use SERVICE as default
    "swimming_pool": FacilityCategory.SERVICE,  # Use SERVICE as default
    "hotel": FacilityCategory.SERVICE,  # Use SERVICE as default
    "hostel": FacilityCategory.SERVICE,  # Use SERVICE as default
    "guest_house": FacilityCategory.SERVICE,  # Use SERVICE as default
    "information": FacilityCategory.INFORMATION,
    "post_office": FacilityCategory.SERVICE,  # Use SERVICE as default
    "police": FacilityCategory.SERVICE,  # Use SERVICE as default
    "fire_station": FacilityCategory.SERVICE,  # Use SERVICE as default
}

# Mapping from OSM building tags to our building categories
OSM_BUILDING_MAPPING = {
    "hotel": BuildingCategory.OTHER,
    "dormitory": BuildingCategory.DORMITORY,
    "house": BuildingCategory.OTHER,
    "residential": BuildingCategory.OTHER,
    "commercial": BuildingCategory.OTHER,
    "retail": BuildingCategory.OTHER,
    "office": BuildingCategory.OFFICE,
    "industrial": BuildingCategory.OTHER,
    "cathedral": BuildingCategory.OTHER,
    "chapel": BuildingCategory.OTHER,
    "church": BuildingCategory.OTHER,
    "mosque": BuildingCategory.OTHER,
    "temple": BuildingCategory.OTHER,
    "synagogue": BuildingCategory.OTHER,
    "shrine": BuildingCategory.OTHER,
    "civic": BuildingCategory.OTHER,
    "college": BuildingCategory.TEACHING_BUILDING,
    "school": BuildingCategory.TEACHING_BUILDING,
    "university": BuildingCategory.TEACHING_BUILDING,
    "public": BuildingCategory.OTHER,
    "hospital": BuildingCategory.OTHER,
    "museum": BuildingCategory.MUSEUM,
    "library": BuildingCategory.LIBRARY,
    "railway_station": BuildingCategory.OTHER,
    "transportation": BuildingCategory.OTHER,
    "government": BuildingCategory.OTHER,
    "roof": BuildingCategory.OTHER,
    "garage": BuildingCategory.OTHER,
    "farm_auxiliary": BuildingCategory.OTHER,
    "barn": BuildingCategory.OTHER,
    "conservatory": BuildingCategory.OTHER,
    "digester": BuildingCategory.OTHER,
    "farm": BuildingCategory.OTHER,
    "greenhouse": BuildingCategory.OTHER,
    "hangar": BuildingCategory.OTHER,
    "hut": BuildingCategory.OTHER,
    "shed": BuildingCategory.OTHER,
    "stable": BuildingCategory.OTHER,
    "sty": BuildingCategory.OTHER,
    "tank": BuildingCategory.OTHER,
    "transformer_tower": BuildingCategory.OTHER,
    "works": BuildingCategory.OTHER,
}


def get_osm_data_for_location(location_name: str) -> Optional[Dict]:
    """Fetch real map data for a specific location using OSM."""
    if not HAS_OSMNX:
        print("osmnx not available, skipping real data fetch")
        return None
    
    try:
        # First get the place boundary from which to extract data
        try:
            gdf_place = ox.geocode_to_gdf(location_name)
            place_bounds = gdf_place.total_bounds if len(gdf_place) > 0 else None
        except:
            place_bounds = None

        # Get building data using features module which is available in newer osmnx
        try:
            buildings = ox.features_from_place(location_name, tags={"building": True})
            if buildings is not None and len(buildings) > 0:
                buildings = buildings.reset_index()
                # Filter for valid building entries
                if 'building' in buildings.columns:
                    buildings = buildings[buildings['building'].notna()]
        except Exception as e:
            print(f"No buildings found for {location_name}: {e}")
            buildings = None
        
        # Get POI data
        try:
            pois = ox.features_from_place(
                location_name,
                tags={
                    "amenity": True,
                    "tourism": True,
                    "leisure": True
                }
            )
            if pois is not None and len(pois) > 0:
                pois = pois.reset_index()
        except Exception as e:
            print(f"No POIs found for {location_name}: {e}")
            pois = None

        # Get street network
        try:
            G = ox.graph_from_place(location_name, network_type="walk", simplify=False)
        except Exception as e:
            print(f"No street network found for {location_name}: {e}")
            G = None
        
        return {
            "location_name": location_name,
            "buildings": buildings,
            "pois": pois,
            "graph": G,
            "bounds": place_bounds
        }
    except Exception as e:
        print(f"Error fetching OSM data for {location_name}: {e}")
        return None


def convert_osm_buildings_to_model(osm_buildings, region_id: int) -> List[Dict]:
    """Convert OSM building data to our internal format."""
    if osm_buildings is None or len(osm_buildings) == 0:
        return []
    
    buildings = []
    building_id = 1
    
    for idx, row in osm_buildings.iterrows():
        try:
            # Get the center point of the building geometry
            geometry = row['geometry']
            if hasattr(geometry, 'centroid'):
                centroid = geometry.centroid
                lat, lon = centroid.y, centroid.x
            else:
                continue  # Skip if geometry doesn't have centroid
            
            # Determine building category from OSM tags
            category = BuildingCategory.OTHER  # Default
            if 'building' in row and row['building'] in OSM_BUILDING_MAPPING:
                category = OSM_BUILDING_MAPPING[row['building']]
            elif 'amenity' in row and row['amenity'] in OSM_FACILITY_MAPPING:
                # This is more of a facility than a building, but we'll include it
                pass
            
            # Get name, use fallback if missing
            name = row.get('name', None)
            if name is None or (hasattr(name, 'lower') and name.lower() == 'nan') or (isinstance(name, float) and str(name).lower() == 'nan'):
                name = f"Building {building_id}"
            
            building = {
                "id": building_id,
                "region_id": region_id,
                "name": name,
                "category": category.value,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            }
            buildings.append(building)
            building_id += 1
        except Exception as e:
            print(f"Error converting building {idx}: {e}")
            continue
    
    return buildings


def convert_osm_pois_to_facilities(osm_pois, region_id: int) -> List[Dict]:
    """Convert OSM POI data to our facility format."""
    if osm_pois is None or len(osm_pois) == 0:
        return []
    
    facilities = []
    facility_id = 1
    
    for idx, row in osm_pois.iterrows():
        try:
            # Get the center point of the POI geometry
            geometry = row['geometry']
            if hasattr(geometry, 'centroid'):
                centroid = geometry.centroid
                lat, lon = centroid.y, centroid.x
            elif hasattr(geometry, 'x') and hasattr(geometry, 'y'):
                # Point geometry
                lat, lon = geometry.y, geometry.x
            else:
                continue  # Skip if geometry doesn't have coordinates
            
            # Determine facility category from OSM tags
            category = FacilityCategory.SERVICE  # Default to SERVICE since OTHER doesn't exist
            
            # Check amenity tag first
            if 'amenity' in row and row['amenity'] in OSM_FACILITY_MAPPING:
                category = OSM_FACILITY_MAPPING[row['amenity']]
            elif 'tourism' in row and row['tourism'] in OSM_FACILITY_MAPPING:
                category = OSM_FACILITY_MAPPING[row['tourism']]
            elif 'leisure' in row and row['leisure'] in OSM_FACILITY_MAPPING:
                category = OSM_FACILITY_MAPPING[row['leisure']]
            elif 'building' in row and row['building'] in OSM_BUILDING_MAPPING:
                # If it's categorized as a building from the building tag, map to appropriate facility
                # though this might be a misclassification in the OSM data
                pass
            
            # Get name, use fallback if missing
            name = row.get('name', None)
            if name is None or (hasattr(name, 'lower') and name.lower() == 'nan') or (isinstance(name, float) and str(name).lower() == 'nan'):
                name = f"Facility {facility_id}"
            
            facility = {
                "id": facility_id,
                "region_id": region_id,
                "name": name,
                "category": category.value,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            }
            facilities.append(facility)
            facility_id += 1
        except Exception as e:
            print(f"Error converting POI {idx}: {e}")
            continue
    
    return facilities


def convert_osm_graph_to_components(osm_graph, region_type: RegionType) -> Tuple[List[Dict], List[Dict]]:
    """Convert an OSM network graph into intersection nodes and bidirectional edges."""

    if osm_graph is None:
        return [], []

    # Determine transport modes based on region type
    if region_type == RegionType.CAMPUS:
        transport_modes = [TransportMode.WALK, TransportMode.BIKE]
    else:  # SCENIC
        transport_modes = [TransportMode.WALK, TransportMode.ELECTRIC_CART]

    nodes: List[Dict] = []
    node_index_map: Dict[int, int] = {}

    for osm_id, data in osm_graph.nodes(data=True):
        try:
            lat = float(data.get("y"))
            lon = float(data.get("x"))
        except (TypeError, ValueError):
            continue

        if math.isfinite(lat) and math.isfinite(lon):
            node_index_map[osm_id] = len(nodes)
            nodes.append(
                {
                    "name": data.get("name"),
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                }
            )

    edges: List[Dict] = []

    for u, v, data in osm_graph.edges(data=True):
        source_index = node_index_map.get(u)
        target_index = node_index_map.get(v)
        if source_index is None or target_index is None:
            continue

        distance = data.get("length", 100.0)
        try:
            distance_val = float(distance)
        except (TypeError, ValueError):
            distance_val = 100.0

        payload = {
            "distance": round(distance_val, 2),
            "ideal_speed": round(random.uniform(0.8, 1.8), 2),
            "congestion": round(random.uniform(0.3, 1.0), 2),
            "transport_modes": [mode.value for mode in transport_modes],
        }

        edges.append({"source_index": source_index, "target_index": target_index, **payload})
        edges.append({"source_index": target_index, "target_index": source_index, **payload})

    return nodes, edges


def build_graph_from_coordinates(
    coordinates: List[Tuple[float, float]],
    region_type: RegionType,
) -> Tuple[List[Dict], List[Dict]]:
    """Fallback: create a dense graph by projecting coordinates onto intersections."""

    if len(coordinates) < 2:
        return [], []

    # Determine transport modes based on region type
    if region_type == RegionType.CAMPUS:
        transport_modes = [TransportMode.WALK, TransportMode.BIKE]
    else:  # SCENIC
        transport_modes = [TransportMode.WALK, TransportMode.ELECTRIC_CART]

    nodes: List[Dict] = [
        {
            "name": None,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
        }
        for lat, lon in coordinates
    ]

    edges: List[Dict] = []
    seen_pairs: set[Tuple[int, int]] = set()

    for idx, (lat, lon) in enumerate(coordinates):
        distances: List[Tuple[float, int]] = []
        for target_idx, (t_lat, t_lon) in enumerate(coordinates):
            if target_idx == idx:
                continue
            distance = math.dist((lat, lon), (t_lat, t_lon)) * 1000
            distances.append((distance, target_idx))
        distances.sort(key=lambda item: item[0])

        for distance, target_idx in distances[: min(4, len(distances))]:
            pair_key = tuple(sorted((idx, target_idx)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            payload = {
                "distance": round(distance, 2),
                "ideal_speed": round(random.uniform(0.8, 1.8), 2),
                "congestion": round(random.uniform(0.3, 1.0), 2),
                "transport_modes": [mode.value for mode in transport_modes],
            }

            edges.append({"source_index": idx, "target_index": target_idx, **payload})
            edges.append({"source_index": target_idx, "target_index": idx, **payload})

    return nodes, edges