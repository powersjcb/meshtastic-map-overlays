import os
import json
import gzip
from collections import Counter

try:
    import geojson
except ImportError:
    print("Please install the 'geojson' package: pip install geojson")
    exit(1)

def analyze_geojson(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = geojson.load(f)
    features = data.get('features', [])
    geom_types = Counter()
    for feat in features:
        geom = feat.get('geometry', {})
        gtype = geom.get('type', 'Unknown')
        geom_types[gtype] += 1
    return {
        'feature_count': len(features),
        'geometry_types': dict(geom_types)
    }

def get_file_size(filepath):
    return os.path.getsize(filepath)

def get_gzipped_size(filepath):
    with open(filepath, 'rb') as f_in:
        gzipped = gzip.compress(f_in.read())
    return len(gzipped)

def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    files = [f for f in os.listdir(directory) if f.endswith('.geojson')]
    print(f"Analyzing {len(files)} GeoJSON files in '{directory}':\n")
    for fname in sorted(files):
        path = os.path.join(directory, fname)
        stats = analyze_geojson(path)
        size = get_file_size(path)
        gzsize = get_gzipped_size(path)
        print(f"{fname}")
        print(f"  Features: {stats['feature_count']}")
        print(f"  Geometry types: {stats['geometry_types']}")
        print(f"  Size: {size/1024:.1f} KB (uncompressed), {gzsize/1024:.1f} KB (gzipped)")
        print()

if __name__ == '__main__':
    main()