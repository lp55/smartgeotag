from PySide6 import QtWebEngineWidgets
from __feature__ import snake_case, true_property
from geo import Coordinates
import folium
import folium.plugins as fplugins
import io
import math


def center(coordinates: list[Coordinates]) -> Coordinates:
    """
    Provides the central coordinate based on a list of coordinates
    """
    if not coordinates:
        return Coordinates(0, 0)

    qtd_coords = len(coordinates)
    x, y, z = 0.0, 0.0, 0.0
    for coord in coordinates:
        latitude = coord.latitude * math.pi / 180
        longitude = coord.longitude * math.pi / 180

        x += math.cos(latitude) * math.cos(longitude)
        y += math.cos(latitude) * math.sin(longitude)
        z += math.sin(latitude)

    x, y, z = [val / qtd_coords for val in (x, y, z)]
    longitude = math.atan2(y, x)
    hypotenuse = math.sqrt(x * x + y * y)
    latitude = math.atan2(z, hypotenuse)

    return Coordinates(latitude * 180 / math.pi, longitude * 180 / math.pi)


def bounds(coordinates: list[Coordinates]) -> tuple[Coordinates, Coordinates]:
    """
    Extract the top left edge and the bottom right edge from a list of coordinates
    """
    if not coordinates:
        return Coordinates(0, 0)

    if len(coordinates) == 1:
        return coordinates[0], coordinates[0]

    top_left = Coordinates(*map(min, zip(*coordinates)))
    bottom_right = Coordinates(*map(max, zip(*coordinates)))

    return top_left, bottom_right


def bounds_and_center(
    coordinates: list[Coordinates],
) -> tuple[tuple[Coordinates, Coordinates], Coordinates]:
    """
    Extract the top left edge and the bottom right edge from a list of coordinates
    """
    if not coordinates:
        return Coordinates(0, 0)

    if len(coordinates) == 1:
        return None, coordinates[0]

    top_left = Coordinates(*map(min, zip(*coordinates)))
    bottom_right = Coordinates(*map(max, zip(*coordinates)))
    center = Coordinates(
        (top_left.latitude + bottom_right.latitude) / 2,
        (top_left.longitude + bottom_right.longitude) / 2,
    )

    return (top_left, bottom_right), center


def set_map(
    web_view: QtWebEngineWidgets.QWebEngineView,
    coordinates: list[Coordinates],
    markers: list[str] = [],
    descriptions: list[str] = [],
    draggable=False,
):
    if not coordinates:
        raise Exception("No valid coordinates passed")

    # if no list of markers was passed, just fill it with a numeric sequence
    if not markers:
        markers = [str(val) for val in range(len(coordinates))]

    if descriptions and len(descriptions) != len(coordinates):
        raise Exception("Descriptions does not match the amount of Coordinates")

    bounds, center = bounds_and_center(coordinates)

    map = folium.Map(title="Coordinates", zoom_start=13, location=center)
    for i in range(len(coordinates)):
        description = (
            descriptions[i]
            if descriptions
            else f"{coordinates[i].latitude}, {coordinates[i].longitude}"
        )

        folium.Marker(
            icon=fplugins.BeautifyIcon(
                icon="arrow-down",
                icon_shape="marker",
                number=markers[i],
                text_color="white",
                border_color="blue",
                background_color="blue",
            ),
            # icon=folium.Icon(icon="9", prefix="fa", color="blue"),
            location=(coordinates[i].latitude, coordinates[i].longitude),
            popup=description,
            draggable=draggable,
        ).add_to(map)

    if bounds:
        map.fit_bounds(bounds)

    data = io.BytesIO()
    map.save(data, close_file=False)
    web_view.set_html(data.getvalue().decode())
    # web_view.set_html(map._repr_html_())


def get_markers(
    web_view: QtWebEngineWidgets.QWebEngineView,
) -> list[tuple[str, str, Coordinates]]:
    map = folium.Map(title="Coordinates", zoom_start=13, location=center)
