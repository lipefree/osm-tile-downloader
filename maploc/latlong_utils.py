# Copyright (c) Meta Platforms, Inc. and affiliates.

# refactoring 

from typing import Dict, Optional, Tuple
from .utils.geo import BoundaryBox, Projection
from . import logger
import numpy as np

try:
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="orienternet")
except ImportError:
    geolocator = None

def process_latlong(
        prior_latlon: Optional[Tuple[float, float]] = None,
        prior_address: Optional[str] = None,
        tile_size_meters: int = 64,
    ):
        latlon = parse_location_prior(prior_latlon, prior_address)
        proj = Projection(*latlon)
        center = proj.project(latlon)
        bbox = BoundaryBox(center, center) + tile_size_meters
        return proj, bbox

def parse_location_prior(
    prior_latlon: Optional[Tuple[float, float]] = None,
    prior_address: Optional[str] = None,
) -> np.ndarray:
    latlon = None
    if prior_latlon is not None:
        latlon = prior_latlon
    elif prior_address is not None:
        if geolocator is None:
            raise ValueError("geocoding unavailable, install geopy.")
        location = geolocator.geocode(prior_address)
        if location is None:
            logger.info("Could not find any location for address '%s.'", prior_address)
        else:
            logger.info("Using prior address '%s'", location.address)
            latlon = (location.latitude, location.longitude)

    return np.array(latlon)