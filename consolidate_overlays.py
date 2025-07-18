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
import math
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configuration - Edit these values as needed
OVERLAYS = [
    {
        "name": "BurningMan",
        "layers": {
            "streetOutlines": {
                "inputFile": "resources/burning_man/Street_Outlines.geojson",
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
                "inputFile": "resources/burning_man/Toilets.geojson",
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
                "inputFile": "resources/burning_man/Trash_Fence.geojson",
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
    #         "layer1": {
    #             "inputFile": "resources/AnotherEvent_Layer1.geojson",
    #             "name": "Layer 1",
    #             "description": "Description of layer 1",
    #             "rendering": {
    #                 "lineColor": "#FF00FF",
    #                 "lineOpacity": 0.7,
    #                 "lineThickness": 1.5,
    #                 "fillOpacity": 0.3
    #             }
    #         },
    #         "layer2": {
    #             "inputFile": "resources/AnotherEvent_Layer2.geojson",
    #             "name": "Layer 2",
    #             "description": "Description of layer 2",
    #             "rendering": {
    #                 "lineColor": "#00FFFF",
    #                 "lineOpacity": 1.0,
    #                 "lineThickness": 2.0,
    #                 "fillOpacity": 0.0
    #             }
    #         }
    #     }
    # }
]

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_svg_preview(config_file: str, output_file: str, width: int = 800, height: int = 600):
    """
    Generate an SVG preview of the overlay configuration.

    Args:
        config_file: Path to the compressed configuration file
        output_file: Path to output SVG file
        width: SVG width in pixels
        height: SVG height in pixels
    """
    print(f"Generating SVG preview: {config_file} -> {output_file}")

    # Load and decompress the configuration
    try:
        with gzip.open(config_file, 'rt', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        return

    # Calculate bounds from all overlays
    bounds = calculate_bounds(config)
    if not bounds:
        print("No valid geometry found for bounds calculation")
        return

    # Calculate scale and offset for SVG
    scale, offset_x, offset_y = calculate_transform(bounds, width, height)

    # Generate SVG content
    svg_content = generate_svg_content(config, bounds, scale, offset_x, offset_y, width, height)

    # Write SVG file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Successfully created SVG preview: {output_file}")
    except Exception as e:
        print(f"Error writing SVG file: {e}")

def calculate_bounds(config: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    """Calculate the bounding box of all overlays."""
    min_lon, min_lat = float('inf'), float('inf')
    max_lon, max_lat = float('-inf'), float('-inf')

    for overlay in config.get('overlays', []):
        geojson = overlay.get('geojson', {})
        for feature in geojson.get('features', []):
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])

            # Extract coordinates based on geometry type
            coords = extract_coordinates(coordinates, geometry.get('type', ''))

            for coord in coords:
                lon, lat = coord[0], coord[1]
                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)

    if min_lon == float('inf'):
        return None

    return (min_lon, min_lat, max_lon, max_lat)

def extract_coordinates(coordinates: Any, geometry_type: str) -> List[List[float]]:
    """Extract all coordinate pairs from geometry."""
    coords = []

    if geometry_type == 'Point':
        coords.append(coordinates)
    elif geometry_type == 'LineString':
        coords.extend(coordinates)
    elif geometry_type == 'Polygon':
        for ring in coordinates:
            coords.extend(ring)
    elif geometry_type == 'MultiPoint':
        coords.extend(coordinates)
    elif geometry_type == 'MultiLineString':
        for line in coordinates:
            coords.extend(line)
    elif geometry_type == 'MultiPolygon':
        for polygon in coordinates:
            for ring in polygon:
                coords.extend(ring)

    return coords

def calculate_transform(bounds: Tuple[float, float, float, float], width: int, height: int) -> Tuple[float, float, float]:
    """Calculate scale and offset for transforming coordinates to SVG space."""
    min_lon, min_lat, max_lon, max_lat = bounds

    # Add padding
    padding = 0.1
    lon_range = (max_lon - min_lon) * (1 + padding)
    lat_range = (max_lat - min_lat) * (1 + padding)

    # Calculate scale to fit in SVG
    scale_x = width / lon_range
    scale_y = height / lat_range
    scale = min(scale_x, scale_y)

    # Calculate offset to center
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    offset_x = width / 2 - center_lon * scale
    offset_y = height / 2 + center_lat * scale  # Flip Y axis

    return scale, offset_x, offset_y

def generate_svg_content(config: Dict[str, Any], bounds: Tuple[float, float, float, float],
                        scale: float, offset_x: float, offset_y: float, width: int, height: int) -> str:
    """Generate the SVG content."""
    min_lon, min_lat, max_lon, max_lat = bounds

    # SVG header
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .overlay {{ stroke-width: 1; }}
      .legend {{ font-family: Arial, sans-serif; font-size: 12px; }}
    </style>
  </defs>

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="#f8f8f8" stroke="#ccc" stroke-width="1"/>

  <!-- Title -->
  <text x="{width//2}" y="20" text-anchor="middle" class="legend" font-weight="bold">
    {config.get('metadata', {}).get('name', 'Overlay Preview')}
  </text>

  <!-- Overlays -->
'''

    # Add each overlay
    for overlay in config.get('overlays', []):
        rendering = overlay.get('rendering', {})
        color = rendering.get('lineColor', '#000000')
        opacity = rendering.get('lineOpacity', 1.0)
        thickness = rendering.get('lineThickness', 1.0)
        fill_opacity = rendering.get('fillOpacity', 0.0)

        # Convert hex to RGB for opacity
        r, g, b = hex_to_rgb(color)

        svg += f'  <!-- {overlay.get("name", "Unknown")} -->\n'
        svg += f'  <g class="overlay" stroke="rgb({r},{g},{b})" stroke-opacity="{opacity}" stroke-width="{thickness}" fill="rgb({r},{g},{b})" fill-opacity="{fill_opacity}">\n'

        # Add geometry
        geojson = overlay.get('geojson', {})
        for feature in geojson.get('features', []):
            geometry = feature.get('geometry', {})
            svg += generate_geometry_svg(geometry, scale, offset_x, offset_y)

        svg += '  </g>\n'

    # Add legend
    svg += generate_legend(config, width, height)

    # Add bounds info
    svg += f'''
  <!-- Bounds Info -->
  <text x="10" y="{height-30}" class="legend" fill="#666">
    Bounds: {min_lon:.4f}, {min_lat:.4f} to {max_lon:.4f}, {max_lat:.4f}
  </text>
  <text x="10" y="{height-15}" class="legend" fill="#666">
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </text>
</svg>'''

    return svg

def generate_geometry_svg(geometry: Dict[str, Any], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG path for a geometry."""
    geometry_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])

    if geometry_type == 'Point':
        return generate_point_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'LineString':
        return generate_linestring_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'Polygon':
        return generate_polygon_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'MultiPoint':
        return generate_multipoint_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'MultiLineString':
        return generate_multilinestring_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'MultiPolygon':
        return generate_multipolygon_svg(coordinates, scale, offset_x, offset_y)

    return ''

def transform_coord(lon: float, lat: float, scale: float, offset_x: float, offset_y: float) -> Tuple[float, float]:
    """Transform geographic coordinates to SVG coordinates."""
    x = lon * scale + offset_x
    y = -lat * scale + offset_y  # Flip Y axis
    return x, y

def generate_point_svg(coordinates: List[float], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for a point."""
    x, y = transform_coord(coordinates[0], coordinates[1], scale, offset_x, offset_y)
    return f'    <circle cx="{x}" cy="{y}" r="3"/>\n'

def generate_linestring_svg(coordinates: List[List[float]], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for a line string."""
    points = []
    for coord in coordinates:
        x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
        points.append(f"{x},{y}")

    path_data = f"M {' L '.join(points)}"
    return f'    <path d="{path_data}"/>\n'

def generate_polygon_svg(coordinates: List[List[List[float]]], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for a polygon."""
    svg = ''
    for ring in coordinates:
        points = []
        for coord in ring:
            x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
            points.append(f"{x},{y}")

        path_data = f"M {' L '.join(points)} Z"
        svg += f'    <path d="{path_data}"/>\n'

    return svg

def generate_multipoint_svg(coordinates: List[List[float]], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for multiple points."""
    svg = ''
    for coord in coordinates:
        x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
        svg += f'    <circle cx="{x}" cy="{y}" r="3"/>\n'
    return svg

def generate_multilinestring_svg(coordinates: List[List[List[float]]], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for multiple line strings."""
    svg = ''
    for line in coordinates:
        points = []
        for coord in line:
            x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
            points.append(f"{x},{y}")

        path_data = f"M {' L '.join(points)}"
        svg += f'    <path d="{path_data}"/>\n'
    return svg

def generate_multipolygon_svg(coordinates: List[List[List[List[float]]]], scale: float, offset_x: float, offset_y: float) -> str:
    """Generate SVG for multiple polygons."""
    svg = ''
    for polygon in coordinates:
        for ring in polygon:
            points = []
            for coord in ring:
                x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
                points.append(f"{x},{y}")

            path_data = f"M {' L '.join(points)} Z"
            svg += f'    <path d="{path_data}"/>\n'
    return svg

def generate_legend(config: Dict[str, Any], width: int, height: int) -> str:
    """Generate a legend for the overlays."""
    legend_x = width - 200
    legend_y = 50
    legend_width = 180
    legend_height = 30 * len(config.get('overlays', [])) + 20

    svg = f'''
  <!-- Legend -->
  <rect x="{legend_x}" y="{legend_y}" width="{legend_width}" height="{legend_height}"
        fill="white" stroke="#ccc" stroke-width="1" opacity="0.9"/>
  <text x="{legend_x + 10}" y="{legend_y + 15}" class="legend" font-weight="bold">Layers</text>
'''

    for i, overlay in enumerate(config.get('overlays', [])):
        rendering = overlay.get('rendering', {})
        color = rendering.get('lineColor', '#000000')
        name = overlay.get('name', 'Unknown')

        y_pos = legend_y + 35 + i * 25

        # Color swatch
        r, g, b = hex_to_rgb(color)
        svg += f'  <rect x="{legend_x + 10}" y="{y_pos - 8}" width="12" height="12" fill="rgb({r},{g},{b})" stroke="#000" stroke-width="0.5"/>\n'

        # Layer name
        svg += f'  <text x="{legend_x + 30}" y="{y_pos}" class="legend">{name}</text>\n'

    return svg

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

        # Write uncompressed configuration for reference
        uncompressed_file = os.path.join(output_dir, f"{overlay_name}GeoJSONMapConfig.json")
        json_str = json.dumps(config, separators=(',', ':'))
        original_size = len(json_str.encode('utf-8'))

        with open(uncompressed_file, 'w', encoding='utf-8') as f:
            f.write(json_str)

        print(f"  Successfully created {uncompressed_file} ({original_size:,} bytes)")

        # Write compressed configuration
        output_file = os.path.join(output_dir, f"{overlay_name}GeoJSONMapConfig.json.gz")

        with gzip.open(output_file, 'wt', encoding='utf-8') as f:
            f.write(json_str)

        compressed_size = os.path.getsize(output_file)
        compression_ratio = (1 - compressed_size / original_size) * 100
        print(f"  Configuration compressed: {original_size:,} bytes -> {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")
        print(f"  Successfully created {output_file}")

        # Generate SVG preview
        svg_output_file = os.path.join(output_dir, f"{overlay_name}GeoJSONMapConfig.svg")
        generate_svg_preview(output_file, svg_output_file)

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
        output_dir = "./output"

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