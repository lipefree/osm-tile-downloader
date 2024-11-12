# Copyright (c) Meta Platforms, Inc. and affiliates.
# modified by lipefree (github name)

import json
from http.client import responses
from pathlib import Path
from typing import Any, Dict, Optional

import urllib3 # type: ignore

from .. import logger
from ..utils.geo import BoundaryBox

OSM_URL = "https://api.openstreetmap.org/api/0.6/map.json" # Very limited rate but fast, good for demo
OVERPASS_URL = "https://overpass-api.de/api/interpreter" # 10k query per day
COFFEE_OVERPASS_URL = "https://overpass.private.coffee/api/interpreter" # unlimited queries 


# We got ban from the OSM API because we wanted to download too much lol
def get_osm_old(
    boundary_box: BoundaryBox,
    cache_path: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    if not overwrite and cache_path is not None and cache_path.is_file():
        return json.loads(cache_path.read_text())

    (bottom, left), (top, right) = boundary_box.min_, boundary_box.max_
    query = {"bbox": f"{left},{bottom},{right},{top}"}
    print('query is ', f"{bottom},{left},{top},{right}")

    result = urllib3.request("GET", OSM_URL, fields=query, timeout=10)
    if result.status != 200:
        error = result.info()["error"]
        raise ValueError(f"{result.status} {responses[result.status]}: {error}")

    if cache_path is not None:
        cache_path.write_bytes(result.data)

    return result.json()


def get_osm(
    boundary_box: BoundaryBox,  
    alt_provider: bool = True, #
    cache_path: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    if not overwrite and cache_path is not None and cache_path.is_file():
        return json.loads(cache_path.read_text())

    (bottom, left), (top, right) = boundary_box.min_, boundary_box.max_

    # Define the Overpass QL query as a string
    overpass_query = f"""
    [out:json][timeout:60];
    (
        node({bottom},{left},{top},{right});
        way({bottom},{left},{top},{right});
        >;
        relation({bottom},{left},{top},{right});
    );
    out body;
    """

    # Create an HTTP manager
    http = urllib3.PoolManager()

    URL = COFFEE_OVERPASS_URL

    # Send the POST request to Overpass API

    try:
        result = http.request(
            "POST",
            URL,
            body=f"data={overpass_query}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60
        )
    except:
        print('Network problem detected')
        raise ValueError

    # Check for errors in the response
    if result.status != 200:
        print('HHTP ERROR')
        error_message = result.data.decode('utf-8') if result.data else "Unknown error"
        raise ValueError(f"{result.status} {responses.get(result.status, 'Unknown Error')}: {error_message}")

    # Cache the result if specified
    if cache_path is not None:
        cache_path.write_bytes(result.data)

    # Parse and return JSON response
    return result.json()