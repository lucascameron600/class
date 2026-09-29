#!/usr/bin/env python3

import json
import statistics
import urllib.request

OSRM = "http://localhost:5000"

# engine -> (station name, lon, lat)
STATIONS = {
    "E03": ("Station 3", -122.4194, 37.7870),  # 1067 Post St between Polk & Larkin (approx; drop a pin to refine)
}

# engine, call location, actual travel seconds, lon, lat
CALLS = [
    ("E03", "Mason St / Post St",        161, -122.41005693,  37.788082187),
    ("E03", "Eddy St / Wagner Aly",      172, -122.413287607, 37.783844774),
    ("E03", "Ellis St / Jones St",       150, -122.412782128, 37.784866246),
    ("E03", "Eddy St / Leavenworth St",  131, -122.414241573, 37.783723783),
    ("E03", "Jones St / O'Farrell St",   251, -122.412969667, 37.785789585),
    ("E03", "Jones St / Post St",        149, -122.413353964, 37.787663599),
    ("E03", "Jones St / Post St",        135, -122.413353964, 37.787663599),
    ("E03", "Ellis St / Hyde St",        117, -122.416071735, 37.784448842),
]


def osrm_seconds(lon1, lat1, lon2, lat2):
    url = f"{OSRM}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    return data["routes"][0]["duration"]


ratios = []
print(f"{'engine':6} {'started at':11} {'call location':24} {'actual':>6} {'osrm':>6} {'ratio':>6}")

for engine, location, actual, lon, lat in CALLS:
    station, st_lon, st_lat = STATIONS[engine]
    osrm = osrm_seconds(st_lon, st_lat, lon, lat)
    ratio = osrm / actual
    ratios.append(ratio)
    print(f"{engine:6} {station:11} {location:24} {actual:6.0f} {osrm:6.0f} {ratio:6.2f}")

print(f"\nmedian OSRM/actual: {statistics.median(ratios):.2f}   (>1 = OSRM too slow, <1 = too fast)")
