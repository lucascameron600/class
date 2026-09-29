#!/usr/bin/env python3

import json
import statistics
import urllib.request

OSRM = "http://localhost:5000"

# engine -> (station name, lon, lat)
STATIONS = {
    "E23": ("Station 23", -122.5048, 37.7607),
}

# engine, call location, actual travel seconds, lon, lat
CALLS = [
    ("E23", "Taraval St / 45th Ave",  240, -122.50355,  37.741814),
    ("E23", "23rd Ave / Irving St",   201, -122.48141,  37.763374),
    ("E23", "Judah St / 25th Ave",    196, -122.48342,  37.761417),
    ("E23", "47th Ave / Balboa St",   210, -122.508026, 37.775227),
    ("E23", "Fulton St / 47th Ave",   216, -122.50775,  37.771496),
    ("E23", "31st Ave / Irving St",   184, -122.48998,  37.762997),
    ("E23", "Lincoln Way / 33rd Ave", 140, -122.492256, 37.76478),
    ("E23", "47th Ave / Ortega St",   168, -122.50635,  37.751053),
    ("E23", "47th Ave / Ortega St",   128, -122.50635,  37.751053),
    ("E23", "47th Ave / Ortega St",    89, -122.50635,  37.751053),
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
