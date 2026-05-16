"""Resolve layer: spatial deduplication + linkage.

Given ObservedBuilding rows (from MS / OSM / future sources) and RegisteredBuilding
rows (from DGU), produce the canonical Building entities the UI talks about.

Algorithm (pilot scale ~4k polygons — brute force with an STRtree prefilter):

1. Union-find on (Observed ∪ Registered) by IoU >= IOU_THRESHOLD.
2. Each connected component becomes one Building. Its geometry is the union of
   member observed footprints (we trust observed over registered for what's on
   the ground today).
3. Write typed Links: building_observed_as, building_registered_as.
4. Each Building's parcel is the Parcel whose polygon contains its centroid.
"""
from app.resolve.resolver import resolve_all

__all__ = ["resolve_all"]
