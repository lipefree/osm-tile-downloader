from maploc.latlong_utils import process_latlong
import numpy as np
from maploc.osm.tiling import TileManager

VIGOR_TILE_SIZE = 72.96  # m
VIGOR_PPM = 640 / 73

def get_osm_raster(latlong: tuple[float, float], tile_size: float = VIGOR_TILE_SIZE, ppm: float = VIGOR_PPM) -> np.ndarray:
    '''
        latlong : latitude/longitude
        tile_size : size of one side (tile is a square only)
        ppm : pixel per meter to manage the resolution of the tile

        Default are using VIGOR dataset metrics
    '''
    # Orienternet black box magic but we do get our osm tile (canvas.raster) at the end

    proj, bbox = process_latlong(
        prior_latlon=latlong, tile_size_meters=tile_size / 2 # type: ignore
    )
    tiler = TileManager.from_bbox(proj, bbox, ppm)  # type: ignore
    canvas = tiler.query(bbox) # type: ignore

    return canvas.raster