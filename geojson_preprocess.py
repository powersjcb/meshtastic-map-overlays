# todos for this script:
# parse the geojson files an we will save them to an output file with no padded whitepaces
# we will round all GPS coordinates to 5 decimal places - approximately 1 meter precision
# we will also remove all the properties from the geojson file
# we will also remove all the geometry types that are not LineString, or Polygon (no points - they add too much clutter in the UI)