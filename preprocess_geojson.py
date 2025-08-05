#!/usr/bin/env python3
"""
Consolidate multiple GeoJSON files into a single GeoJSON FeatureCollection with embedded styling.

This script processes individual GeoJSON files and combines them into a single standard
GeoJSON FeatureCollection where each feature has styling properties embedded in its
'properties' object, conforming to the GeoJSON styling specification.

OUTPUT SCHEMA:
The output GeoJSON follows RFC 7946 with embedded styling properties in each feature:

{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point|LineString|Polygon|MultiPoint|MultiLineString|MultiPolygon",
        "coordinates": [...]
      },
      "properties": {
        // Layer metadata
        "layer_id": "string",          // Internal layer identifier
        "layer_name": "string",        // Human-readable layer name
        "description": "string",       // Layer description

        // Shared properties (all geometries)
        "visible": boolean,            // Whether to display (default: true)

        // Point/MultiPoint styling
        "marker-color": "#rrggbb",     // Marker fill color
        "marker-size": "small|medium|large", // Marker size
        "marker-symbol": "string",     // Optional icon name or emoji

        // Line/MultiLineString styling
        "stroke": "#rrggbb",          // Line color
        "stroke-width": number,       // Line width in pixels
        "stroke-opacity": number,     // Line transparency (0-1)
        "line-dasharray": [n,n,...],  // Optional dash pattern

        // Polygon/MultiPolygon styling
        "fill": "#rrggbb",           // Fill color
        "fill-opacity": number,      // Fill transparency (0-1)
        "stroke": "#rrggbb",         // Border color
        "stroke-width": number,      // Border width in pixels
        "stroke-opacity": number,    // Border transparency (0-1)
        "line-dasharray": [n,n,...]  // Optional border dash pattern
      }
    }
  ]
}

SUPPORTED GEOMETRY EXAMPLES:

Point:
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [-119.21612, 40.8029]},
  "properties": {
    "layer_id": "toilets", "layer_name": "Toilets",
    "description": "Portable toilet locations",
    "marker-color": "#4169E1", "marker-size": "medium", "visible": true
  }
}

LineString:
{
  "type": "Feature",
  "geometry": {"type": "LineString", "coordinates": [[-119.21612, 40.8029], [-119.21608, 40.80293]]},
  "properties": {
    "layer_id": "roads", "layer_name": "Roads",
    "description": "Street network",
    "stroke": "#90EE90", "stroke-width": 2.0, "stroke-opacity": 1.0, "visible": true
  }
}

Polygon:
{
  "type": "Feature",
  "geometry": {"type": "Polygon", "coordinates": [[[lon,lat], [lon,lat], [lon,lat], [lon,lat]]]},
  "properties": {
    "layer_id": "zones", "layer_name": "Event Zones",
    "description": "Event boundary areas",
    "fill": "#FF0000", "fill-opacity": 0.3,
    "stroke": "#000000", "stroke-width": 1.0, "stroke-opacity": 0.8, "visible": true
  }
}

MultiPoint:
{
  "type": "Feature",
  "geometry": {"type": "MultiPoint", "coordinates": [[-119.21612, 40.8029], [-119.21608, 40.80293]]},
  "properties": {
    "layer_id": "services", "layer_name": "Services",
    "description": "Service locations",
    "marker-color": "#32CD32", "marker-size": "small", "visible": true
  }
}

MultiLineString:
{
  "type": "Feature",
  "geometry": {"type": "MultiLineString", "coordinates": [[[lon,lat], [lon,lat]], [[lon,lat], [lon,lat]]]},
  "properties": {
    "layer_id": "trails", "layer_name": "Trails",
    "description": "Walking paths",
    "stroke": "#8B4513", "stroke-width": 1.5, "stroke-opacity": 0.8, "visible": true
  }
}

MultiPolygon:
{
  "type": "Feature",
  "geometry": {"type": "MultiPolygon", "coordinates": [[[[lon,lat], [lon,lat], [lon,lat], [lon,lat]]]]},
  "properties": {
    "layer_id": "buildings", "layer_name": "Buildings",
    "description": "Structure footprints",
    "fill": "#D2691E", "fill-opacity": 0.7,
    "stroke": "#000000", "stroke-width": 1.0, "stroke-opacity": 1.0, "visible": true
  }
}

REFERENCES:
- RFC 7946 - GeoJSON standard: https://datatracker.ietf.org/doc/html/rfc7946
- Mapbox SimpleStyle Spec: https://github.com/mapbox/simplestyle-spec
- Leaflet Style Functions: https://leafletjs.com/examples/geojson/
- Mapbox GL Style Specification: https://docs.mapbox.com/mapbox-gl-js/style-spec/

Usage: python3 consolidate_overlays.py [output_directory]
"""

import json
import zlib
import os
import sys
import math
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configuration - Edit these values as needed
# TODO: Add validation that the config is valid for all required fields (rendering properties, file paths)
OVERLAYS = [
    {
        "name": "BurningMan",
        "layers": {
            "streetOutlines": {
                "inputFile": "resources/burning_man/2025/street_outlines.geojson",
                "name": "Street Outlines",
                "description": "Main street outlines and roads",
                "simplificationStrategy": "douglas_peucker",
                "simplificationTolerance": 0.000005,
                "rendering": {
                    "lineColor": "#333333", # dark grey
                    "lineOpacity": 1.0,
                    "lineThickness": 1.0,
                    "fillOpacity": 0.0
                }
            },
            "trashFence": {
                "inputFile": "resources/burning_man/2025/trash_fence.geojson",
                "name": "Trash Fence",
                "description": "Event boundary and trash fence",
                "simplificationStrategy": "none",
                "rendering": {
                    "lineColor": "#FFA500", # orange plastic fence dust faded color
                    "lineOpacity": 1.0,
                    "lineThickness": 1.0,
                    "fillOpacity": 0.0
                }
            },
            "cpns": {
                "inputFile": "resources/burning_man/2025/cpns.geojson",
                "name": "CPNS",
                "description": "CPNS locations",
                "simplificationStrategy": "none",
                "rendering": {
                    "lineColor": "#FFA500", # dark salmon
                    "lineOpacity": 1.0,
                    "lineThickness": 1.0,
                    "fillOpacity": 1.0
                }
            },
            "toilets": {
                "inputFile": "resources/burning_man/2025/toilets.geojson",
                "name": "Toilets",
                "description": "Portable toilet locations",
                "simplificationStrategy": "rectangle",
                "simplificationTolerance": 0.000005,
                "rendering": {
                    "lineColor": "#0000FF", # blue
                    "lineOpacity": 1.0,
                    "lineThickness": 1.0,
                    "fillOpacity": 0.7
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

def convert_rendering_to_geojson_style(rendering_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert internal rendering configuration to GeoJSON style properties."""
    style_props = {}

    # Map line/stroke properties
    if 'lineColor' in rendering_config:
        style_props['stroke'] = rendering_config['lineColor']

    if 'lineOpacity' in rendering_config:
        style_props['stroke-opacity'] = rendering_config['lineOpacity']

    if 'lineThickness' in rendering_config:
        style_props['stroke-width'] = rendering_config['lineThickness']

    # Map fill properties
    if 'fillOpacity' in rendering_config:
        style_props['fill-opacity'] = rendering_config['fillOpacity']
        # Set fill color same as stroke if fill is visible
        if rendering_config['fillOpacity'] > 0 and 'lineColor' in rendering_config:
            style_props['fill'] = rendering_config['lineColor']
        elif rendering_config['fillOpacity'] == 0:
            style_props['fill'] = '#000000'  # Default, but will be transparent

    # For points, map to marker properties
    if 'lineColor' in rendering_config:
        style_props['marker-color'] = rendering_config['lineColor']

    # Set marker size based on thickness or use default
    thickness = rendering_config.get('lineThickness', 1.0)
    if thickness <= 1.0:
        style_props['marker-size'] = 'small'
    elif thickness <= 2.0:
        style_props['marker-size'] = 'medium'
    else:
        style_props['marker-size'] = 'large'

    # Default to visible
    style_props['visible'] = True

    return style_props

def generate_svg_preview(geojson_file: str, output_file: str, width: int = 800, height: int = 600):
    """
    Generate an SVG preview of the GeoJSON data.

    Args:
        geojson_file: Path to the GeoJSON file
        output_file: Path to output SVG file
        width: SVG width in pixels
        height: SVG height in pixels
    """
    print(f"Generating SVG preview: {geojson_file} -> {output_file}")

    # Load the GeoJSON data
    try:
        with open(geojson_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return

    # Calculate bounds from GeoJSON features
    bounds = calculate_geojson_bounds(geojson_data)
    if not bounds:
        print("No valid geometry found for bounds calculation")
        return

    # Calculate scale and offset for SVG
    scale, offset_x, offset_y = calculate_transform(bounds, width, height)

    # Generate SVG content
    svg_content = generate_geojson_svg_content(geojson_data, bounds, scale, offset_x, offset_y, width, height)

    # Write SVG file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Successfully created SVG preview: {output_file}")
    except Exception as e:
        print(f"Error writing SVG file: {e}")

def calculate_geojson_bounds(geojson_data: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    """Calculate the bounding box of GeoJSON features."""
    min_lon, min_lat = float('inf'), float('inf')
    max_lon, max_lat = float('-inf'), float('-inf')

    for feature in geojson_data.get('features', []):
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

def generate_geojson_svg_content(geojson_data: Dict[str, Any], bounds: Tuple[float, float, float, float],
                               scale: float, offset_x: float, offset_y: float, width: int, height: int) -> str:
    """Generate the SVG content from GeoJSON data."""
    min_lon, min_lat, max_lon, max_lat = bounds

    # SVG header
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .feature {{ stroke-width: 1; }}
      .legend {{ font-family: Arial, sans-serif; font-size: 10px; }}
    </style>
  </defs>

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="#f8f8f8" stroke="#ccc" stroke-width="1"/>

  <!-- Title -->
  <text x="{width//2}" y="20" text-anchor="middle" class="legend" font-weight="bold">
    {geojson_data.get('metadata', {}).get('name', 'GeoJSON Preview')}
  </text>

  <!-- Features -->
'''

    # Add each feature
    for feature in geojson_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        # Get styling from properties
        color = properties.get('stroke', properties.get('marker-color', '#000000'))
        opacity = properties.get('stroke-opacity', 1.0)
        thickness = properties.get('stroke-width', 1.0)
        fill_opacity = properties.get('fill-opacity', 0.0)
        fill_color = properties.get('fill', color)

        # Convert hex to RGB for opacity
        r, g, b = hex_to_rgb(color)
        fill_r, fill_g, fill_b = hex_to_rgb(fill_color)

        layer_name = properties.get('layer_name', 'Unknown')
        svg += f'  <!-- {layer_name} -->\n'
        svg += f'  <g class="feature" stroke="rgb({r},{g},{b})" stroke-opacity="{opacity}" stroke-width="{thickness}" fill="rgb({fill_r},{fill_g},{fill_b})" fill-opacity="{fill_opacity}">\n'

        # Add geometry
        svg += generate_geometry_svg(geometry, scale, offset_x, offset_y, properties)

        svg += '  </g>\n'

    svg += '</svg>'
    return svg

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
      .legend {{ font-family: Arial, sans-serif; font-size: 10px; }}
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

    return svg

def generate_geometry_svg(geometry: Dict[str, Any], scale: float, offset_x: float, offset_y: float, properties: Dict[str, Any] = {}) -> str:
    """Generate SVG path for a geometry."""
    geometry_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])

    if geometry_type == 'Point':
        return generate_point_svg(coordinates, scale, offset_x, offset_y, properties)
    elif geometry_type == 'LineString':
        return generate_linestring_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'Polygon':
        return generate_polygon_svg(coordinates, scale, offset_x, offset_y)
    elif geometry_type == 'MultiPoint':
        return generate_multipoint_svg(coordinates, scale, offset_x, offset_y, properties)
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

def generate_point_svg(coordinates: List[float], scale: float, offset_x: float, offset_y: float, properties: Dict[str, Any] = {}) -> str:
    """Generate SVG for a point with optional text label."""
    x, y = transform_coord(coordinates[0], coordinates[1], scale, offset_x, offset_y)
    svg = f'    <circle cx="{x}" cy="{y}" r="3"/>\n'

    # Add text label if this is a CPN point
    if properties.get('layer_id') == 'cpns' and 'NAME' in properties:
        name = properties.get('NAME', '')
        # Escape special XML characters
        name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
        # Position text slightly above the point
        svg += f'    <text x="{x}" y="{y-5}" text-anchor="middle" font-size="8" fill="black">{name}</text>\n'

    return svg

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

def generate_multipoint_svg(coordinates: List[List[float]], scale: float, offset_x: float, offset_y: float, properties: Dict[str, Any] = {}) -> str:
    """Generate SVG for multiple points."""
    svg = ''
    for coord in coordinates:
        x, y = transform_coord(coord[0], coord[1], scale, offset_x, offset_y)
        svg += f'    <circle cx="{x}" cy="{y}" r="3"/>\n'

        # Add text label if this is a CPN point
        if properties.get('layer_id') == 'cpns' and 'NAME' in properties:
            name = properties.get('NAME', '')
            # Escape special XML characters
            name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
            # Position text slightly above the point
            svg += f'    <text x="{x}" y="{y-5}" text-anchor="middle" font-size="10" fill="black">{name}</text>\n'
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

def load_license_and_attribution():
    """Load license and attribution information from files."""
    license_text = ""
    attribution_text = ""

    # Load LICENSE file
    license_path = "LICENSE"
    if os.path.exists(license_path):
        with open(license_path, 'r', encoding='utf-8') as f:
            license_text = f.read().strip()

    # Load ATTRIBUTION.md file
    attribution_path = "ATTRIBUTION.md"
    if os.path.exists(attribution_path):
        with open(attribution_path, 'r', encoding='utf-8') as f:
            attribution_text = f.read().strip()

    return license_text, attribution_text

def consolidate_overlays(output_dir: str):
    """Consolidate multiple GeoJSON files into a single GeoJSON file with embedded styling."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load license and attribution information
    license_text, attribution_text = load_license_and_attribution()

    total_files_processed = 0
    total_features_processed = 0

    for overlay_config in OVERLAYS:
        overlay_name = overlay_config["name"]
        layers = overlay_config["layers"]

        print(f"\nProcessing overlay: {overlay_name}")

        # Create a single GeoJSON FeatureCollection with metadata
        consolidated_geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "name": f"{overlay_name} GeoJSON Map Data",
                "description": "Consolidated GeoJSON data with embedded styling",
                "generated": datetime.now().isoformat(),
                "license": license_text,
                "attribution": attribution_text,
                "disclaimer": "This project is not affiliated, endorsed, or verified by Burning Man Project",
                "source": "https://github.com/burningmantech/innovate-GIS-data",
                "usage_terms": "Non-commercial use only. See license for full terms."
            },
            "features": []
        }

        total_features = 0

        for layer_id, layer_config in layers.items():
            filepath = layer_config["inputFile"]
            print(f"  Processing {layer_id} from {filepath}")

            # Load and preprocess GeoJSON
            geojson_data = load_and_preprocess_geojson(filepath, layer_config)
            if not geojson_data:
                print(f"Error: Failed to load {filepath}")
                exit(1)

            feature_count = len(geojson_data.get('features', []))
            total_features += feature_count
            print(f"    Loaded {feature_count} features")

            # Add styling properties to each feature based on rendering config
            styling_properties = convert_rendering_to_geojson_style(layer_config["rendering"])

            for feature in geojson_data.get('features', []):
                # Ensure properties object exists
                if 'properties' not in feature:
                    feature['properties'] = {}

                # Add layer metadata
                feature['properties']['layer_id'] = layer_id
                feature['properties']['layer_name'] = layer_config["name"]
                feature['properties']['description'] = layer_config["description"]

                # Add styling properties
                feature['properties'].update(styling_properties)

                # Add to consolidated collection
                consolidated_geojson['features'].append(feature)

        print(f"  Consolidated {len(layers)} layers with {total_features} total features")

        # Write consolidated GeoJSON file
        output_file = os.path.join(output_dir, f"{overlay_name}.geojson")
        json_str = json.dumps(consolidated_geojson, separators=(',', ':'))
        file_size = len(json_str.encode('utf-8'))

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)

        print(f"  Successfully created {output_file} ({file_size:,} bytes)")

        # generate svg preview
        svg_output_file = os.path.join(output_dir, f"{overlay_name}.svg")
        generate_svg_preview(output_file, svg_output_file)

        total_files_processed += 1
        total_features_processed += total_features

    print(f"\nCompleted processing {total_files_processed} GeoJSON files with {total_features_processed} total features")

def load_and_preprocess_geojson(filepath: str, layer_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        processed_data = preprocess_geojson(data, layer_config)
        return processed_data

    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def preprocess_geojson(data: Dict[str, Any], layer_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocess GeoJSON data to reduce file size and normalize format.

    This applies the following optimizations:
    - Truncate coordinates to 5 decimal places (~1m precision)
    - Remove unnecessary properties
    - Filter to only LineString and Polygon geometries
    - Apply simplification based on layer configuration
    """
    processed_features = []

    # Get simplification strategy and tolerance
    strategy = layer_config.get("simplificationStrategy", "none")
    tolerance = layer_config.get("simplificationTolerance", 0.0)
    no_compression = layer_config.get("noCompression", False)

    for feature in data.get('features', []):
        geometry = feature.get('geometry', {})
        geometry_type = geometry.get('type', '')

        # Filter to only supported geometry types
        if geometry_type not in ['Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon']:
            continue

        # Apply simplification FIRST (before coordinate truncation)
        if no_compression:
            # Disable all simplification - keep original geometry
            simplified_geometry = geometry
        elif strategy == "rectangle" and geometry_type in ['Polygon', 'MultiPolygon']:
            # Use rectangle simplification
            simplified_geometry = simplify_to_rectangle(geometry)
        elif strategy == "douglas_peucker" and tolerance > 0:
            # Use Douglas-Peucker simplification
            simplified_geometry = simplify_geometry(geometry, tolerance)
        else:
            # No simplification
            simplified_geometry = geometry

        # THEN truncate coordinates to 5 decimal places (final step)
        truncated_geometry = truncate_coordinates(simplified_geometry)

        processed_feature = {
            'type': 'Feature',
            'geometry': truncated_geometry,
            'properties': feature.get('properties', {}).copy()  # Preserve original properties
        }

        # Include ID if present
        if 'id' in feature:
            processed_feature['id'] = feature['id']

        processed_features.append(processed_feature)

    return {
        'type': 'FeatureCollection',
        'features': processed_features
    }

def simplify_geometry(geometry: Dict[str, Any], tolerance: float) -> Dict[str, Any]:
    """
    Simplify geometry using Douglas-Peucker algorithm to reduce point count.

    Args:
        geometry: GeoJSON geometry object
        tolerance: Simplification tolerance in degrees (default: 0.000001 ~ 0.11m)

    Returns:
        Simplified geometry object
    """
    geometry_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])

    if not coordinates:
        return geometry

    simplified_geometry = geometry.copy()

    if geometry_type == 'LineString':
        simplified_geometry['coordinates'] = douglas_peucker(coordinates, tolerance)
    elif geometry_type == 'Polygon':
        simplified_geometry['coordinates'] = [
            douglas_peucker(ring, tolerance) for ring in coordinates
        ]
    elif geometry_type == 'MultiLineString':
        simplified_geometry['coordinates'] = [
            douglas_peucker(line, tolerance) for line in coordinates
        ]
    elif geometry_type == 'MultiPolygon':
        simplified_geometry['coordinates'] = [
            [douglas_peucker(ring, tolerance) for ring in polygon]
            for polygon in coordinates
        ]

    return simplified_geometry

def douglas_peucker(points: List[List[float]], tolerance: float) -> List[List[float]]:
    """
    Douglas-Peucker line simplification algorithm.

    Args:
        points: List of [lon, lat] coordinate pairs
        tolerance: Maximum perpendicular distance for point removal

    Returns:
        Simplified list of coordinate pairs
    """
    if len(points) <= 2:
        return points

    # Find the point with maximum distance from line segment
    max_distance = 0
    max_index = 0

    # Line segment from first to last point
    start = points[0]
    end = points[-1]

    for i in range(1, len(points) - 1):
        distance = perpendicular_distance(points[i], start, end)
        if distance > max_distance:
            max_distance = distance
            max_index = i

    # If max distance is greater than tolerance, recursively simplify
    if max_distance > tolerance:
        # Recursively simplify the two sub-lines
        left = douglas_peucker(points[:max_index + 1], tolerance)
        right = douglas_peucker(points[max_index:], tolerance)

        # Combine results (avoid duplicate point at max_index)
        return left[:-1] + right
    else:
        # All points between start and end can be removed
        return [start, end]

def perpendicular_distance(point: List[float], line_start: List[float], line_end: List[float]) -> float:
    """
    Calculate the perpendicular distance from a point to a line segment.

    Args:
        point: [lon, lat] coordinate
        line_start: [lon, lat] start of line segment
        line_end: [lon, lat] end of line segment

    Returns:
        Perpendicular distance in degrees
    """
    x, y = point[0], point[1]
    x1, y1 = line_start[0], line_start[1]
    x2, y2 = line_end[0], line_end[1]

    # If line segment is a point, return distance to that point
    if x1 == x2 and y1 == y2:
        return math.sqrt((x - x1) ** 2 + (y - y1) ** 2)

    # Calculate perpendicular distance
    # Formula: |(y2-y1)x - (x2-x1)y + x2*y1 - y2*x1| / sqrt((y2-y1)^2 + (x2-x1)^2)
    numerator = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)

    return numerator / denominator

def truncate_coordinates(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """Truncate coordinates to 5 decimal places for ~1m precision (good visual quality)."""
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

def simplify_to_rectangle(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert any polygon to a simple 4-point axis-aligned rectangle.
    For toilets, we want consistent orientation rather than optimal rotation.

    Args:
        geometry: GeoJSON geometry object (should be Polygon or MultiPolygon)

    Returns:
        Simplified geometry as a 4-point rectangle
    """
    geometry_type = geometry.get('type', '')
    coordinates = geometry.get('coordinates', [])

    if not coordinates:
        return geometry

    # Extract all coordinates from the geometry
    all_coords = []

    if geometry_type == 'Polygon':
        # Extract all coordinates from all rings
        for ring in coordinates:
            all_coords.extend(ring)

    elif geometry_type == 'MultiPolygon':
        # Extract all coordinates from all polygons and rings
        for polygon in coordinates:
            for ring in polygon:
                all_coords.extend(ring)

    else:
        # Not a polygon, return original
        return geometry

    if len(all_coords) < 3:
        return geometry

    # Use simple axis-aligned bounding box for consistent orientation
    rectangle_coords = calculate_simple_bounding_box(all_coords)

    return {
        'type': 'Polygon',
        'coordinates': [rectangle_coords]
    }

def calculate_centroid(coordinates: List[List[float]]) -> List[float]:
    """
    Calculate the centroid of a polygon or multipolygon.
    This is a simplified approach and might not be accurate for all shapes.
    """
    if not coordinates:
        return [0, 0]

    # For a single polygon, sum all points and divide by count
    if isinstance(coordinates[0], (int, float)):
        # Handle single coordinate pair [lon, lat]
        return [coordinates[0], coordinates[1]]
    elif isinstance(coordinates[0], list):
        # Handle array of coordinate pairs
        cx = sum(p[0] for p in coordinates) / len(coordinates)
        cy = sum(p[1] for p in coordinates) / len(coordinates)
        return [cx, cy]
    else:
        return [0, 0] # Fallback

def calculate_minimum_bounding_rectangle(coordinates: List[List[float]]) -> List[List[float]]:
    """
    Calculate the minimum bounding rectangle for a set of coordinates.
    Simple approach: find the two farthest points, then find the perpendicular direction.

    Args:
        coordinates: List of [lon, lat] coordinate pairs

    Returns:
        List of 5 coordinate pairs forming a closed rectangle
    """
    if len(coordinates) < 3:
        return coordinates

    # Find the two points that are farthest apart
    max_distance = 0
    p1, p2 = None, None

    for i in range(len(coordinates)):
        for j in range(i + 1, len(coordinates)):
            dist = distance(coordinates[i], coordinates[j])
            if dist > max_distance:
                max_distance = dist
                p1, p2 = coordinates[i], coordinates[j]

    if p1 is None or p2 is None:
        return calculate_simple_bounding_box(coordinates)

    # Calculate the direction vector of the line between p1 and p2
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)

    if length == 0:
        return calculate_simple_bounding_box(coordinates)

    # Normalize the direction vector
    dx /= length
    dy /= length

    # Perpendicular direction (rotate 90 degrees)
    perp_dx = -dy
    perp_dy = dx

    # Project all points onto both directions to find the extents
    min_parallel = max_parallel = 0
    min_perp = max_perp = 0

    for point in coordinates:
        # Project onto the main direction
        proj_parallel = (point[0] - p1[0]) * dx + (point[1] - p1[1]) * dy
        min_parallel = min(min_parallel, proj_parallel)
        max_parallel = max(max_parallel, proj_parallel)

        # Project onto the perpendicular direction
        proj_perp = (point[0] - p1[0]) * perp_dx + (point[1] - p1[1]) * perp_dy
        min_perp = min(min_perp, proj_perp)
        max_perp = max(max_perp, proj_perp)

    # Calculate the four corners of the rectangle
    corners = []

    # Bottom-left
    x = p1[0] + min_parallel * dx + min_perp * perp_dx
    y = p1[1] + min_parallel * dy + min_perp * perp_dy
    corners.append([x, y])

    # Bottom-right
    x = p1[0] + max_parallel * dx + min_perp * perp_dx
    y = p1[1] + max_parallel * dy + min_perp * perp_dy
    corners.append([x, y])

    # Top-right
    x = p1[0] + max_parallel * dx + max_perp * perp_dx
    y = p1[1] + max_parallel * dy + max_perp * perp_dy
    corners.append([x, y])

    # Top-left
    x = p1[0] + min_parallel * dx + max_perp * perp_dx
    y = p1[1] + min_parallel * dy + max_perp * perp_dy
    corners.append([x, y])

    # Close the polygon
    corners.append(corners[0])

    return corners

def distance(p1: List[float], p2: List[float]) -> float:
    """Calculate Euclidean distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)

def calculate_simple_bounding_box(coordinates: List[List[float]]) -> List[List[float]]:
    """
    Calculate a simple axis-aligned bounding box for a set of coordinates.

    Args:
        coordinates: List of [lon, lat] coordinate pairs

    Returns:
        List of 5 coordinate pairs forming a closed rectangle
    """
    if len(coordinates) < 3:
        return coordinates

    # Find min/max coordinates
    min_lon = min(coord[0] for coord in coordinates)
    max_lon = max(coord[0] for coord in coordinates)
    min_lat = min(coord[1] for coord in coordinates)
    max_lat = max(coord[1] for coord in coordinates)

    # Create rectangle corners (counterclockwise)
    rectangle = [
        [min_lon, min_lat],  # Bottom-left
        [max_lon, min_lat],  # Bottom-right
        [max_lon, max_lat],  # Top-right
        [min_lon, max_lat],  # Top-left
        [min_lon, min_lat]   # Close the polygon
    ]

    return rectangle

def count_total_points(geojson_data: Dict[str, Any]) -> int:
    """Count total number of coordinate points in GeoJSON data."""
    total_points = 0

    for feature in geojson_data.get('features', []):
        geometry = feature.get('geometry', {})
        coordinates = geometry.get('coordinates', [])
        geometry_type = geometry.get('type', '')

        total_points += count_geometry_points(coordinates, geometry_type)

    return total_points

def count_geometry_points(coordinates: Any, geometry_type: str) -> int:
    """Count points in a single geometry."""
    if not coordinates:
        return 0

    if geometry_type == 'Point':
        return 1
    elif geometry_type == 'LineString':
        return len(coordinates)
    elif geometry_type == 'Polygon':
        return sum(len(ring) for ring in coordinates)
    elif geometry_type == 'MultiPoint':
        return len(coordinates)
    elif geometry_type == 'MultiLineString':
        return sum(len(line) for line in coordinates)
    elif geometry_type == 'MultiPolygon':
        return sum(sum(len(ring) for ring in polygon) for polygon in coordinates)

    return 0


output_dir = "./output"


if __name__ == "__main__":
    # Get output directory from command line argument or use default

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