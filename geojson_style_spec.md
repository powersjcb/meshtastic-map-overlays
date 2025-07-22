# 🧭 GeoJSON Styling Specification for Renderer Integration

## 🎯 Purpose
This specification defines the supported styling properties embedded in the `properties` field of each GeoJSON `Feature` to control how geometries should be rendered in mapping frameworks like Mapbox GL, MapLibre, Leaflet, or custom renderers.

---

## 🧾 Feature-Level Properties

Each `Feature` in the GeoJSON may include the following **optional** keys inside its `properties` object.

> **Note**: All colors must be in CSS-compatible formats (e.g., `"#rrggbb"` or `"rgba(r, g, b, a)"`).

### 🔲 Shared Across All Geometry Types

| Property      | Type      | Default  | Description                        |
|---------------|-----------|----------|------------------------------------|
| `title`       | `string`  | `""`     | Optional name or label             |
| `description` | `string`  | `""`     | Optional human-readable description|
| `visible`     | `boolean` | `true`   | Whether to display the feature     |

---

### 🔶 Polygon Styling (`type: Polygon` or `MultiPolygon`)

| Property         | Type      | Default     | Description                             |
|------------------|-----------|-------------|-----------------------------------------|
| `fill`           | `string`  | `"#000000"` | Fill color                              |
| `fill-opacity`   | `number`  | `1.0`       | Fill transparency (0–1)                 |
| `stroke`         | `string`  | `"#000000"` | Border (outline) color                  |
| `stroke-width`   | `number`  | `1`         | Outline width in pixels                 |
| `stroke-opacity` | `number`  | `1.0`       | Outline transparency (0–1)              |
| `line-dasharray` | `array`   | `null`      | Optional dash pattern, e.g., `[4, 2]`   |

---

### 📏 Line Styling (`type: LineString` or `MultiLineString`)

| Property         | Type      | Default     | Description                        |
|------------------|-----------|-------------|------------------------------------|
| `stroke`         | `string`  | `"#000000"` | Line color                         |
| `stroke-width`   | `number`  | `2`         | Line width in pixels               |
| `stroke-opacity` | `number`  | `1.0`       | Line transparency (0–1)            |
| `line-dasharray` | `array`   | `null`      | Dash pattern, e.g., `[5, 5]`       |

---

### 🔘 Point Styling (`type: Point` or `MultiPoint`)

| Property        | Type      | Default     | Description                              |
|-----------------|-----------|-------------|------------------------------------------|
| `marker-color`  | `string`  | `"#000000"` | Marker fill color                        |
| `marker-size`   | `string`  | `"medium"`  | Size: `"small"`, `"medium"`, `"large"`   |
| `marker-symbol` | `string`  | `null`      | Optional icon name or emoji              |

---

## 🧠 Example Feature

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[...], [...], [...], [...]]]
  },
  "properties": {
    "title": "Restricted Area",
    "fill": "#ff0000",
    "fill-opacity": 0.3,
    "stroke": "#000000",
    "stroke-width": 2,
    "stroke-opacity": 0.8,
    "visible": true
  }
}
```

---

## 🛠 Implementation Guidance

- If a property is missing, use the default from this spec.
- Unknown properties should be ignored gracefully.
- Support fallback using `coalesce` or `??` when generating Mapbox-style expressions.
- You may preprocess these into a separate style object for rendering engines that separate data from style.

---

## 📚 References

- [RFC 7946 - GeoJSON standard](https://datatracker.ietf.org/doc/html/rfc7946)
- [Mapbox SimpleStyle Spec](https://github.com/mapbox/simplestyle-spec)
- [Leaflet Style Functions](https://leafletjs.com/examples/geojson/)
- [Mapbox GL Style Specification](https://docs.mapbox.com/mapbox-gl-js/style-spec/)

