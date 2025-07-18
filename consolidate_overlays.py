#!/usr/bin/env python3
"""
Consolidate multiple GeoJSON files into compressed configuration files.

This script takes individual GeoJSON files and combines them into multiple
JSON configuration files with embedded GeoJSON data and rendering properties,
then compresses them with gzip for efficient storage in the iOS app bundle.

Usage: python3 consolidate_overlays.py [output_directory]
"""

import json
import gzip
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration - Edit these values as needed
OVERLAYS = [
    {
        "name": "BurningMan",
        "layers": {
            "streetOutlines": {
                "inputFile": "resources/Street_Outlines.geojson",
                "name": "Street Outlines",
                "description": "Main street outlines and roads",
                "rendering": {
                    "lineColor": "#00FF00",
                    "lineOpacity": 0.8,
                    "lineThickness": 0.5,
                    "fillOpacity": 0.0
                }
            },
            "toilets": {
                "inputFile": "resources/Toilets.geojson",
                "name": "Toilets",
                "description": "Portable toilet locations",
                "rendering": {
                    "lineColor": "#0000FF",
                    "lineOpacity": 1.0,
                    "lineThickness": 2.0,
                    "fillOpacity": 1.0
                }
            },
            "trashFence": {
                "inputFile": "resources/Trash_Fence.geojson",
                "name": "Trash Fence",
                "description": "Event boundary and trash fence",
                "rendering": {
                    "lineColor": "#FF0000",
                    "lineOpacity": 1.0,
                    "lineThickness": 2.0,
                    "fillOpacity": 0.0
                }
            }
        }
    }
    # Add more overlay configurations here as needed:
    # {
    #     "name": "AnotherEvent",
    #     "layers": {
    #         "layer1": { ... },
    #         "layer2": { ... }
    #     }
    # }
]

def consolidate_overlays(output_dir: str):
    """Consolidate multiple GeoJSON files into configuration files."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    total_files_processed = 0
    total_features_processed = 0

    for overlay_config in OVERLAYS:
        overlay_name = overlay_config["name"]
        layers = overlay_config["layers"]

        print(f"\nProcessing overlay: {overlay_name}")

        config = {
            "version": "1.0",
            "metadata": {
                "name": f"{overlay_name} Overlays",
                "description": f"Map overlays for {overlay_name} event",
                "generated": datetime.now().isoformat()
            },
            "overlays": []
        }

        total_features = 0

        for layer_id, layer_config in layers.items():
            filepath = layer_config["inputFile"]
            print(f"  Processing {layer_id} from {filepath}")

            # Load and preprocess GeoJSON
            geojson_data = load_and_preprocess_geojson(filepath)
            if not geojson_data:
                print(f"Error: Failed to load {filepath}")
                exit(1)

            feature_count = len(geojson_data.get('features', []))
            total_features += feature_count
            print(f"    Loaded {feature_count} features")

            # Create overlay definition
            overlay = {
                "id": layer_id,
                "name": layer_config["name"],
                "description": layer_config["description"],
                "rendering": layer_config["rendering"],
                "geojson": geojson_data
            }

            config["overlays"].append(overlay)

        print(f"  Consolidated {len(config['overlays'])} layers with {total_features} total features")

        # Write compressed configuration
        output_file = os.path.join(output_dir, f"{overlay_name}GeoJSONMapConfig.json.gz")
        json_str = json.dumps(config, separators=(',', ':'))
        original_size = len(json_str.encode('utf-8'))

        with gzip.open(output_file, 'wt', encoding='utf-8') as f:
            f.write(json_str)

        compressed_size = os.path.getsize(output_file)
        compression_ratio = (1 - compressed_size / original_size) * 100
        print(f"  Configuration compressed: {original_size:,} bytes -> {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")
        print(f"  Successfully created {output_file}")

        total_files_processed += 1
        total_features_processed += total_features

    print(f"\nCompleted processing {total_files_processed} overlay configurations with {total_features_processed} total features")

def load_and_preprocess_geojson(filepath: str) -> Optional[Dict[str, Any]]:
    """Load and preprocess a GeoJSON file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate GeoJSON structure
        if data.get('type') != 'FeatureCollection':
            print(f"Error: {filepath} is not a FeatureCollection")
            return None

        features = data.get('features', [])
        if not features:
            print(f"Error: {filepath} has no features")
            return None

        # Apply preprocessing
        processed_data = preprocess_geojson(data)
        return processed_data

    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def preprocess_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess GeoJSON data to reduce file size and normalize format.

    This applies the following optimizations:
    - Truncate coordinates to 5 decimal places (~1m precision)
    - Remove unnecessary properties
    - Filter to only LineString and Polygon geometries
    """
    processed_features = []

    for feature in data.get('features', []):
        geometry = feature.get('geometry', {})
        geometry_type = geometry.get('type', '')

        # Filter to only supported geometry types
        if geometry_type not in ['LineString', 'Polygon', 'MultiLineString', 'MultiPolygon']:
            continue

        # Truncate coordinates to 5 decimal places
        truncated_geometry = truncate_coordinates(geometry)

        # Keep minimal properties
        properties = feature.get('properties', {})
        cleaned_properties = {k: v for k, v in properties.items() if k in ['ref', 'name', 'type']}

        processed_feature = {
            'type': 'Feature',
            'geometry': truncated_geometry,
            'properties': cleaned_properties if cleaned_properties else None
        }

        # Include ID if present
        if 'id' in feature:
            processed_feature['id'] = feature['id']

        processed_features.append(processed_feature)

    return {
        'type': 'FeatureCollection',
        'features': processed_features
    }

def truncate_coordinates(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """Truncate coordinates to 5 decimal places for ~1m precision."""
    def truncate_coord_array(coords):
        if isinstance(coords[0], (int, float)):
            # Single coordinate pair [lon, lat]
            return [round(coords[0], 5), round(coords[1], 5)]
        else:
            # Array of coordinates
            return [truncate_coord_array(coord) for coord in coords]

    truncated_geometry = geometry.copy()
    coordinates = geometry.get('coordinates', [])

    if coordinates:
        truncated_geometry['coordinates'] = truncate_coord_array(coordinates)

    return truncated_geometry

if __name__ == "__main__":
    # Get output directory from command line argument or use default
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "../meshtastic-apple/Meshtastic/Resources"

    print(f"Output directory: {output_dir}")

    # Check that all input files exist
    missing_files = []
    for overlay_config in OVERLAYS:
        for layer_id, layer_config in overlay_config["layers"].items():
            if not os.path.exists(layer_config["inputFile"]):
                missing_files.append(layer_config["inputFile"])

    if missing_files:
        print("Error: Missing input files:")
        for f in missing_files:
            print(f"  {f}")
        exit(1)

    # Consolidate overlays
    try:
        consolidate_overlays(output_dir)
        exit(0)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)