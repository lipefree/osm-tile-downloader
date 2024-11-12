from ast import Tuple
from curses.ascii import isupper
import os
import gzip
import pickle

from typing import List
from maploc.latlong_utils import process_latlong
from maploc.osm.tiling import TileManager
from osm_tile import get_osm_raster
import numpy as np

from tqdm import tqdm

# only works for VIGOR dataset
root = "../../VIGOR/"  
VIGOR_TILE_SIZE = 72.96  # m


def prepare_osm_data(dataset_root: str, test_mode: bool = False) -> None:
    """
    Main function of this file

    We want to download the tiles if they are not already downloaded

    The tiles are saved per city as a data.pkl.gz in the osm_tiles directory of each city
    directory.

    path : VIGOR/{city}/osm_tiles/data.pkl.gz
    """
    # check if osm data is already downloaded
    downloaded: bool = is_osm_tiles_downloaded(dataset_root)

    if downloaded:
        print(
            "OSM tiles detected",
            "\n remove all VIGOR/{city}/osm_tiles/data.pkl.gy to redownload tiles",
        )
        return  # already downloaded, exit

    print(
        "OSM tiles are not present, will be downloaded now. It will take a very long time, around 6 hours per city."
    )

    print("cities : ", city_list(dataset_root))

    # Each city will have a subfolder 'osm_tiles' with the data
    create_dirs(dataset_root)

    download_tiles(dataset_root, test_mode)

    print("OSM tiles are now downloaded")


def download_tiles(dataset_root: str, test_mode: bool = False) -> None:
    """
    TODO: host the files somewhere instead
    """
    cities = city_list(dataset_root)
    for city in cities:
        if already_downloaded_for(dataset_root, city):
            print(
                f"tiles for {city} already present \n"
            )  # Since download time is long, we may have downloaded tiles for some cities
        else:
            print("downloading tiles for : ", city)
            if test_mode:
                test_download_per_city(dataset_root, city)
            else:
                try:
                    download_per_city(dataset_root, city)
                except ValueError:
                    print(
                        "The API returned an error. Please try later or check private coffee status online"
                    )
                    return


def already_downloaded_for(dataset_root: str, city: str) -> bool:
    osm_tiles_path = os.path.join(dataset_root, city, "osm_tiles", "data.pkl.gz")
    if not os.path.isfile(osm_tiles_path):
        return False

    with gzip.open(osm_tiles_path, "rb") as f:
        length_loaded_data = len(pickle.load(f))
        length_latlong_list = len(list_latlong(dataset_root, city))

        return length_loaded_data == length_latlong_list


def test_download_per_city(dataset_root: str, city: str) -> None:
    """
    Since downloading osm tiles takes around 1 day, this function helps debug the model while the tiles are downloaded
    """

    latlong_list = list_latlong(dataset_root, city)
    print(len(latlong_list), " tiles for ", city)

    print("TEST MODE")
    rasterized_map_list = []

    holder = get_osm_raster(latlong_list[0][1])
    for name, latlong in tqdm(latlong_list, desc=f"Processing tiles for {city}"):
        rasterized_map_list.append((name, holder))

    osm_dir_path = os.path.join(dataset_root, city, "osm_tiles")
    with gzip.open(os.path.join(osm_dir_path, "data.pkl.gz"), "wb") as f:
        pickle.dump(rasterized_map_list, f)


def download_per_city(dataset_root: str, city: str) -> None:
    """
    This simply downloads but has a backup mechanism in case private coffee is not stable.
    """
    latlong_list = list_latlong(dataset_root, city)
    print(len(latlong_list), " tiles for ", city)

    rasterized_map_list = []

    osm_tiles_path = os.path.join(dataset_root, city, "osm_tiles", "data.pkl.gz")
    if os.path.isfile(osm_tiles_path):
        with gzip.open(osm_tiles_path, "rb") as f:
            loaded_data = pickle.load(f)
            rasterized_map_list.extend(loaded_data)

    size_backup = len(rasterized_map_list)
    if size_backup > 0:
        print(f"{size_backup} pre-downloaded tiles for {city} detected")

    for i, (name, latlong) in enumerate(
        tqdm(latlong_list[size_backup:], desc=f"Processing tiles for {city}")
    ):
        try:
            m = get_osm_raster(latlong)
        except:
            dump_rasterized_list(
                dataset_root, city, rasterized_map_list
            )  # early dump in case private coffee has problems
            print("error from API instance. Downloaded data are saved")
            raise ValueError  # Propagate error

        rasterized_map_list.append((name, m))

        if i % 10_000 == 0:
            dump_rasterized_list(dataset_root, city, rasterized_map_list)

    dump_rasterized_list(dataset_root, city, rasterized_map_list)


def dump_rasterized_list(dataset_root: str, city: str, rasterized_map_list) -> None:
    osm_dir_path = os.path.join(dataset_root, city, "osm_tiles")
    with gzip.open(os.path.join(osm_dir_path, "data.pkl.gz"), "wb") as f:
        pickle.dump(rasterized_map_list, f)


# def get_osm_raster(latlong: tuple[float, float]) -> np.ndarray:
#     # Orienternet black box magic but we do get our osm tile (canvas.raster) at the end

#     proj, bbox = process_latlong(
#         prior_latlon=latlong, tile_size_meters=VIGOR_TILE_SIZE / 2
#     )
#     ppm = 640 / 73  # To get 640x640 pixels at the end
#     tiler = TileManager.from_bbox(proj, bbox, ppm)  # type: ignore
#     canvas = tiler.query(bbox)

#     return canvas.raster


def list_latlong(dataset_root: str, city: str) -> List[tuple[str, tuple[float, float]]]:
    """
    We will get the list of lat/long by parsing the file
    in /VIGOR/splits_new/{city}/satellite_list.txt since the lines look like:
        satellite_41.87337878187409_-87.69119741060825.png

    and it the order for the dataloarder
    """
    satellite_list_file = os.path.join(
        dataset_root, "splits_new", city, "satellite_list.txt"
    )

    latlong_list = []

    with open(satellite_list_file, "r") as file:
        for line in file.readlines():
            latlong_list.append((line, latlong_from_file_name(line)))

    return latlong_list


def latlong_from_file_name(file_name: str) -> tuple[float, float]:
    """
    satellite_41.87337878187409_-87.69119741060825.png => (41.87337878187409, 87.69119741060825)
    """

    coordinates = file_name.replace("satellite_", "").replace(".png", "")
    lat, lon = map(float, coordinates.split("_"))
    return (lat, lon)


def create_dirs(dataset_root: str) -> None:
    cities = city_list(dataset_root)
    for city in cities:
        path = os.path.join(dataset_root, city, "osm_tiles")
        try:
            os.makedirs(path)
        except:
            print(f"dir for {city} tiles already present")


def is_osm_tiles_downloaded(dataset_root: str) -> bool:

    # check if osm data is already downloaded by looking if dir exists
    cities = city_list(dataset_root)
    for city in cities:
        if not os.path.isdir(os.path.join(dataset_root, city, "osm_tiles")):
            return False
        else:
            if not os.path.isfile(
                os.path.join(dataset_root, city, "osm_tiles", "data.pkl.gz")
            ):
                return False

    return True


def city_list(dataset_root: str) -> List[str]:
    dirs = os.listdir(dataset_root)
    cities = []
    for dir in dirs:
        if dir[0].isupper():
            cities.append(dir)

    return cities


if __name__ == "__main__":
    prepare_osm_data(root, test_mode=False)
