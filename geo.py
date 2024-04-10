from pathlib import Path

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from geopy.location import Location


from pyexiv2 import Image as ImageExiv2

from typing import NamedTuple
from enum import Enum
from dataclasses import dataclass
from time import sleep
import fractions
from functools import lru_cache

batch = []
batch_size = 950
min_size = 1024 * 1024

images_extensions = [
    ".jpeg",
    ".jpg",
    ".dng",
    ".tif",
    ".mov",
    ".png",
    ".mpg",
    ".psd",
]


class CoordinateType(Enum):
    Latitude = 0
    Longitude = 1


class Coordinates(NamedTuple):
    latitude: float
    longitude: float


class Fraction(fractions.Fraction):
    def __new__(cls: "Fraction", value: float, ignore=None):
        return fractions.Fraction.from_float(value).limit_denominator(99999)


class Degrees(NamedTuple):
    degrees: Fraction
    minutes: Fraction
    seconds: Fraction
    quad: str

    def __str__(self) -> str:
        return f"{float(self.degrees):g}º{float(self.minutes):G}'{float(self.seconds):g}\"{self.quad}"


@dataclass
class GPS:
    latitude_degrees: Degrees
    longitude_degrees: Degrees
    coordinates: Coordinates

    @classmethod
    def from_exif(
        cls: "GPS", latitude: str, latitude_ref: str, longitude: str, longitude_ref: str
    ) -> "GPS":
        latitude_degrees = exif_to_degrees(
            latitude, latitude_ref, CoordinateType.Latitude
        )
        longitude_degrees = exif_to_degrees(
            longitude, longitude_ref, CoordinateType.Longitude
        )

        if not latitude_degrees:
            raise Exception(f"Invalid latitude data: {latitude} {latitude_ref}")
        if not longitude_degrees:
            raise Exception(f"Invalid longitude data: {longitude} {longitude_ref}")

        coordinates = Coordinates(
            degrees_to_decimal(latitude_degrees), degrees_to_decimal(longitude_degrees)
        )
        return cls(
            latitude_degrees,
            longitude_degrees,
            coordinates,
        )

    def degrees_to_exif(self, coordinate_type: CoordinateType) -> str:
        prefix = f"{coordinate_type.name}_degrees".lower()
        return " ".join(
            f"{val.numerator}/{val.denominator}"
            for val in [
                getattr(getattr(self, prefix), coord)
                for coord in ["degrees", "minutes", "seconds"]
            ]
        )

    def latitude_to_exif(self) -> str:
        return self.degrees_to_exif(CoordinateType.Latitude)

    def longitude_to_exif(self) -> str:
        return self.degrees_to_exif(CoordinateType.Longitude)

    def to_exif(self) -> dict[str:str]:
        return {
            "Exif.GPSInfo.GPSLatitude": self.latitude_to_exif(),
            "Exif.GPSInfo.GPSLatitudeRef": self.latitude_degrees.quad,
            "Exif.GPSInfo.GPSLongitude": self.longitude_to_exif(),
            "Exif.GPSInfo.GPSLongitudeRef": self.longitude_degrees.quad,
            "Exif.GPSInfo.GPSMapDatum": "WGS-84",
        }

    @classmethod
    def from_decimal(cls: "GPS", latitude: float, longitude: float) -> "GPS":
        latitude_degrees = decimal_to_degrees(latitude, CoordinateType.Latitude)
        longitude_degrees = decimal_to_degrees(longitude, CoordinateType.Longitude)

        return cls(
            latitude_degrees, longitude_degrees, Coordinates(latitude, longitude)
        )


def folders(path: Path) -> list[str]:
    result = []

    if not path.is_dir():
        path = path.parent

    while str(path) != str(path.anchor):
        result.append(path.stem)
        path = path.parent

    result.append(path.anchor)

    return result[::-1]


def get_coordinates(location: str) -> Coordinates | None:
    geolocator = Nominatim(user_agent="geo")
    count = 1
    while count < 5:
        try:
            gps_location = geolocator.geocode(location)
            if gps_location:
                return Coordinates(
                    gps_location.latitude,
                    gps_location.longitude,
                )
        except GeocoderTimedOut as e:
            sleep(1)
            count += 1
        except Exception as e:
            print(f"Error: {e}")
            break

    print(f"Unable to get gps coordinates for {location}!")


def get_suggestions(location: str) -> list[tuple[str, Coordinates]]:
    geolocator = Nominatim(user_agent="geo")
    count = 1
    while count < 5:
        try:
            gps_locations: list[Location] = geolocator.geocode(
                location, exactly_one=False, limit=5, timeout=5
            )
            return [
                (location.address, Coordinates(location.latitude, location.longitude))
                for location in gps_locations
            ]
        except GeocoderTimedOut as e:
            sleep(1)
            count += 1
        except Exception as e:
            print(f"Error: {e}")
            break

    print(f"Unable to get gps coordinates for {location}!")
    return []


def valid_gps_tags(tags: dict[str:str]) -> bool:
    return all(
        [
            tag in tags.keys()
            for tag in [
                "GPSLatitude",
                "GPSLatitudeRef",
                "GPSLongitude",
                "GPSLongitudeRef",
            ]
        ]
    )


def get_gps_data(file: Path) -> Coordinates | None:
    try:
        with ImageExiv2(str(file)) as img:
            for data in [img.read_exif(), img.read_xmp()]:
                gps_info = {}
                for key, value in data.items():
                    if "GPSInfo" in key:
                        gps_info[key[13:]] = value
                    if "datetime" not in gps_info and "Exif.Image.DateTime" in data:
                        gps_info["datetime"] = data["Exif.Image.DateTime"]
                if valid_gps_tags(gps_info):
                    return gps_info
    except Exception as e:
        print(f"Error reading exif information from file {file}: {e}")


@lru_cache(maxsize=2048)
def get_image_gps(file: Path) -> Coordinates | None:
    sidecar = file.with_suffix(f"{file.suffix}.xmp")
    if sidecar.exists():
        if result := get_gps_data(file):
            return result

    return get_gps_data(file)


def convert_string_degree(value: str) -> Fraction | None:
    try:
        if "/" in value:
            v = value.split(sep="/")
            if len(v) != 2:
                return None
            f = Fraction(float(v[0]) / float(v[1]))
            return f
        else:
            return Fraction(value)
    except Exception as e:
        print(f"Error converting value to a float: {e}")
        return None


def exif_to_degrees(
    value: str, quad: str, coord_type: CoordinateType
) -> Degrees | None:
    coords = value.split()
    if len(coords) != 3:
        return None
    degrees, minutes, seconds = [convert_string_degree(val) for val in coords]

    if any([v is None for v in [degrees, minutes, seconds, quad]]):
        return None

    quad = quad.upper()

    if coord_type == CoordinateType.Latitude and quad not in ["N", "S"]:
        return None
    elif coord_type == CoordinateType.Longitude and quad not in ["W", "E"]:
        return None

    return Degrees(degrees, minutes, seconds, quad)


def degrees_to_decimal(value: Degrees) -> float:
    adjust = 1 if value.quad in ["N", "E"] else -1

    return (
        float(value.degrees) + float(value.minutes) / 60 + float(value.seconds) / 3600
    ) * adjust


def decimal_to_degrees(
    value: float, quad: CoordinateType = CoordinateType.Latitude
) -> Degrees:
    if quad == CoordinateType.Latitude:
        quad = "S" if value < 0 else "N"
    else:
        quad = "W" if value < 0 else "E"

    value = abs(value)

    min, sec = divmod(value * 3600, 60)
    deg, min = divmod(min, 60)

    return Degrees(Fraction(deg), Fraction(min), Fraction(sec), quad)


def write_gps_sidecar(file: Path, latitude: float, longitude: float, overwrite: bool):
    if not file.is_file() or file.suffix.lower() not in images_extensions:
        return

    file = file.with_suffix(f"{file.suffix}.xmp")

    if not overwrite and file.exists():
        return

    if not file.exists():
        sidecar_stub = """<?xml version='1.0' encoding='UTF-8'?>
            <x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Image::ExifTool 12.72'>
            <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
            </rdf:RDF>
            </x:xmpmeta>
            """
        file.write_text(sidecar_stub)
    with ImageExiv2(str(file)) as img:
        if latitude and longitude:
            try:
                gps_data: GPS = GPS.from_decimal(float(latitude), float(longitude))

                img.modify_exif(gps_data.to_exif())
            except:
                print(f"Failed to create GPS data for {latitude} / {longitude}")


def has_subdirectories(dir: Path) -> bool:
    for item in dir.iterdir():
        if item.is_dir():
            return True

    return False


def process_dir(dir: Path) -> list[list[str, str, str, str]]:
    try:
        result = []
        for item in dir.iterdir():
            if item.is_dir():
                if any([val in str(item) for val in ["LPCel", "KCel"]]):
                    continue
                if has_subdirectories(item):
                    result += process_dir(item)
                else:
                    possible_location = "".join(
                        filter(
                            lambda x: not x.isdigit() and not x.isspace(),
                            folders(item)[-1],
                        )
                    )
                    result.append([str(item), possible_location, "", ""])

        return result

    except Exception as error:
        print("Error on folder {}: {}".format(dir, error))


def create_sidecars(data: list[tuple[str, float, float]], overwrite: bool = False):
    for path, latitude, longitude in data:
        path = Path(path)
        if not path.exists():
            print(f"{path} does not exist. Skipping.")
            continue
        if path.is_dir():
            print(f"Processing folder {path}...")
            for item in path.iterdir():
                write_gps_sidecar(item, latitude, longitude, overwrite)
        else:
            write_gps_sidecar(path, latitude, longitude, overwrite)
