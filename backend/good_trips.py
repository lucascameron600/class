#here, take our cleaned trips, our cleaned stations, and then we combine them to build
#solid trips that we think are usable for prediction

# important considerations from data and Large Network Travel Time Distributions for Ambulances

# 1.) needs to have a solid starting point, "origin" -> filter on turnout time, if a unit smacks the button instantly
# they were likely on the road already, SF CAD checks gps locations and puts units en route instantly
# quite often rest of the preesses are within the next 10 seconds

# 2.) A straight line cutoff between start and end node, < 400m too close could uturn or be noisy

# 3.) A secondsary routed distance cutoff to make sure extremely low travel times dont make it in



#GOAL: output a parquet that matches the trip population of map

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import VARIABLES

OSRM_URL = ""


# ALL DROP CRITERIA
# predictor of on road status, unit presses button quickly
# means they were likely in vehicle
# this is a judgement call, based on visaulaizaion of data
MIN_TURNOUT_SECONDS = 20
MAX_TURNOUT_SECONDS = 180    # catch overhead and missed presses of enroute status, discard for unreliable


#based on the paper, catches noise and double backs
MIN_STRAIGHT_METERS = 400
# extra catch for short travel times
MIN_ROUTE_METERS = 400


#not sure about this yet
MAX_DETOUR_RATIO =

# loosley based on paper,
# have to exclude only outlier time segments
# designed to be loose cutoffs to mitigate losing data
# remove any real data
MIN_ROUTE_SPEED = 5
MAX_ROUTE_SPEED = 90


############################################################################
######### HELPERS ##########################################################
############################################################################


def haversine(lat1, lon1, lat2, lon2):
    # reference: https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-  and-distance-between-two-gps-points

    R = 6372.8 # this is in km
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 =radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))

    return R * c * 1000 #outputs in meters



def one_osrm_route(from_lat, from_lon, to_lat, to_lon):
    ## returns the route in meters and  the total route seconds
    url = f"http://localhost:5000/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=false"

    #json format
    http_response = osrm_session.get(url, timeout=1)
    response = http_response.json()

    if response.get("code") != "Ok":
        return np.nan, np.nan, np.nan

    route = response['routes'][0]
    return route['distance'], route['duration']


def flag_all_osrm_route(dataframe, from_cols, to_cols, name):
    # route all combos then add back to trip
    coordinates = from_cols + to_cols

    unique_pairs = {dataframe[coordinates].drop_duplicates().copy()}
    print(f'routing {len(unique_pairs):,} unique pairs')

    results = []

    for pair in unique_pairs.itertuples():
        distance_meters, duration_seconds = osrm_route(row.from_lat, row.from_lon, row.to_lat, row.to_lon)

        results.append('{name}_meters': distance_meters, '{name}_duration': duration_seconds})

    results = pd.DataFrame(results, index=unique_pairs.index)
    routed_pairs = unique_pairs.join(route_results)

    # give every original trip its matching OSRM result.
    return dataframe.merge(routed_pairs, on=coordinates, how="left")



def add_home_station(dataframe):

    extracted = dataframe['unit_id'].astype("string").str.extract(r'(\d+)', expand=False) #gets only digits

    dataframe['home_station'] = pd.to_numeric(extracted).astype('Int64')
    print(f"engines with no station: {dataframe['home_station'].isna().sum():,}")
    return dataframe

#def add_station_coords(dataframe)


def keep_code3_engines_first_dispatched(dataframe):
    ##first dispatched only one trip per incident
    ## one engine leaving its station to the area of the call
    mask = calls['unit_type'].isin(['engine'])
    calls = calls[mask]


def keep_plausible_fromstation(dataframe):
    ## did this unit start at its station? according to exploratory visualization,
    ## a clean predictor of weather a unit is at station, is how fast the unit presses the button
    ## attempts to deal with crews forgetting to press button
    ## Westgate 2015 paper solved wtih gps map matching
    mask = dataframe['turnout_seconds'].between(MIN_TURNOUT_SECONDS, MAX_TURNOUT_SECONDS)
    return dataframe[mask]


def keep_straight_line_distance():
    ## drop calls that are within 400m GCD of the staion
    ## mostly noise based on toronto paper

def keep_routed_distance()
    ## route call with osrm and see if it is over 400 meters, and
    ## also
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
