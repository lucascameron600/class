#here, we take our cleaned trips, our cleaned stations, and then we combine them to build
#solid trips that we think are usable for prediction

# important considerations from data and Large Network Travel Time Distributions for Ambulances

# 1.) needs to have a solid starting point, "origin" -> filter on turnout time, if a unit smacks the button instantly
# they were cheating or on the road already, SF CAD checks gps locations and puts units en route instantly
# quite often rest of the preesses are within the next 10 seconds

# 2.) A straight line cutoff between start and end node, < 400m too close and probably adds noise

# 3.)


##Already have idle_time_seconds

#GOAL: output a parquet that matches the trip population of map

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import VARIABLES

OSRM_URL = "http://localhost:5000"


# ALL DROP CRITERIA
# predictor of on road status, unit presses button quickly
# means they were likely in vehicle
# this is a judgement call, based on visaulaizaion of data
MIN_TURNOUT_SECONDS = 20
MAX_TURNOUT_SECONDS = 180    # catch overhead and missed presses of enroute status, discard for unreliable


#based on the paper, catches noise and double backs
MIN_STRAIGHT_METERS = 400
# extra catch for short travel timesj
MIN_ROUTE_METERS = 400


#not sure about this yet
MAX_DETOUR_RATIO =

# loosley based on paper,
# have to exclude nonsensical time segments
# designed to be loose cutoffs, so we dont
# remove any real data
MIN_ROUTE_SPEED = 5
MAX_ROUTE_SPEED = 90


############################################################################
######### HELPERS ##########################################################
############################################################################

def haversine_meters(lat1, lon1, lat2, lon2):
    #GREAT CIRCLE DISTANCE ON (LAT,LON) (LAT,LON)
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * np.arcsin(np.sqrta(a))



def osrm_route(from_lat, from_lon, to_lat, to_lon):
    ## returns the route in meters and  the total route seconds
    url = f"{OSRM_URL}/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=false"

    #json format
    response = osrm_session.get(url, timeout = 1).json()

    if response.get("code") != "Ok":
        return np.nan, np.nan, np.nan

    route = response['routes'][0]

    return route['distance'], route['duration']


def add_osrm_route(dataframe, from_cols, to_cols, name):


def add_home_station(dataframe):
    extracted = dataframe['unit_id'].astype("string").str.extract(r'(\d+)', expand=False)
    dataframe['home_station'] = pd.to_numeric(extracted).astype('Int64')
    print(f"engines with no home station: {dataframe['home_station'].isna().sum():,}")
    return dataframe

#def add_station_coords(dataframe)


def keep_code3_engines_first_dispatched(dataframe):
    ##first dispatched only, one trip per incident.
    ## the trips match the map aka one engine leaving its station to the area of the call
    ## could also try all code 3 engines

    mask = calls['unit_type'].isin(['engine'])
    calls = calls[mask]


def keep_plausible_fromstation(dataframe):
    ## did this unit start at its station? according to exploratory visualization,
    ## a clean predictor of weather a unit is at station, is how fast the unit presses the button
    ## some stations might press the button too early but from what I have seen
    ## this is suprisingly low and possibly localized to a few stations(unchecked)
    ## might hurt on certain stations


def keep_straight_line_distance():
    ## drop calls that are within 400m GCD of the staion
    ## mostly noise based on toronto paper

def keep_routed_distance()
    ## route call with osrm and see if it is over 400 meters, and
    ## also
def
def main():
    start_time = time.perf_counter()

    calls = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)

    keep_code3_engines_first_dispatched(calls)
    add_home_station(calls)
    add_station_coords(calls)
    keep_plausible_fromstation(calls)
    keep_enough_idle_time(calls)
    keep_straight_line_distance(calls)
    keep_routed_distance(calls)
    keep_plausible_speed(calls)




if __name__ == "__main__":
    main()
