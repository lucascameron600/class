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
import requests

import VARIABLES


osrm_sesh = requests.Session()

############################################################################
############ ALL DROP CRITERIA #############################################
############################################################################

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
MAX_DETOUR_RATIO = None #TODO

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
    # reference: https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points

    R = 6372.8 # this is in km radius of earth
    dLat = np.radians(lat2 - lat1)
    dLon = np.radians(lon2 - lon1)
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    a = np.sin(dLat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dLon/2)**2
    c = 2*np.arcsin(np.sqrt(a))

    return R * c * 1000 #outputs in meters



def one_osrm_route(from_lat, from_lon, to_lat, to_lon):
    ## returns the route in meters and  the total route seconds
    url = f"http://localhost:5000/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=false"

    #json format
    http_response = osrm_sesh.get(url, timeout=1)
    response = http_response.json()

    if response.get("code") != "Ok":
        return np.nan, np.nan

    route = response['routes'][0]
    return route['distance'], route['duration']


def flag_all_osrm_route(dataframe, from_cols, to_cols, name):
    # route all combos then add back to trip
    # from_cols = [lat,lon] to_cols = [lat,lon]

    coordinates = from_cols + to_cols
    unique_pairs = dataframe[coordinates].drop_duplicates().copy()
    print(f'routing {len(unique_pairs):,} unique pairs')

    results = []
    for _i, from_lat, from_lon, to_lat, to_lon in unique_pairs.itertuples():
        distance_meters, duration_seconds = one_osrm_route(from_lat, from_lon, to_lat, to_lon)
        results.append({f'{name}_meters': distance_meters, f'{name}_duration': duration_seconds})

    # give results the same index as our unique pairs
    results = pd.DataFrame(results, index=unique_pairs.index)
    routed_pairs = unique_pairs.join(results)

    return dataframe.merge(routed_pairs, on=coordinates, how="left")



def add_home_station(dataframe):

    extracted = dataframe['unit_id'].astype("string").str.extract(r'(\d+)', expand=False) #expand false gets series instead of dataframe

    dataframe['home_station'] = pd.to_numeric(extracted).astype('Int64')
    print(f"engines with no station: {dataframe['home_station'].isna().sum():,}")
    return dataframe

def add_station_coords(dataframe):
    return dataframe # INPROG


def flag_dropped(dataframe, keep_mask, reason):
    keep_mask = keep_mask.fillna(False).astype(bool)
    newly_dropped = ~keep_mask & dataframe['drop_reason'].isna()
    dataframe.loc[newly_dropped, 'drop_reason'] = reason
    print(f"  dropped {reason:<20}: {newly_dropped.sum():,}")
    return dataframe

############################################################################
##################### MAIN FILTERS #########################################
############################################################################

def keep_code3_engines_first_dispatched(dataframe):
    ##first dispatched only one trip per incident
    ## one engine leaving its station to the area of the call
    mask = dataframe['unit_type'].isin(['ENGINE'])
    ## TODO: first dispatched
    return dataframe[mask].copy()


def keep_plausible_fromstation(dataframe):
    ## did this unit start at its station? according to exploratory visualization,
    ## a clean predictor of weather a unit is at station, is how fast the unit presses the button
    ## attempts to deal with crews forgetting to press button
    ## Westgate 2015 paper solved wtih gps map matching
    mask = dataframe['turnout_seconds'].between(MIN_TURNOUT_SECONDS, MAX_TURNOUT_SECONDS)

    return flag_dropped(dataframe, mask, ': turnout exclusion')


def keep_enough_idle_time(dataframe):
    return dataframe #INPROG


def keep_straight_line_distance(dataframe):
    ## drop calls that are within 400m GCD of the staion
    ## mostly noise based on toronto paper
    return dataframe #INPROG


def keep_routed_distance(dataframe):
    ## route call with osrm and see if it is over 400 meters, and
    return dataframe #INPROG


def keep_plausible_speed(dataframe):

    return dataframe #INPROG


######## REPLACE ME #################################
def compare_kept_vs_dropped(dataframe):
    status = dataframe['drop_reason'].fillna('KEPT')
    print(status.value_counts().to_string())

    cols = ['idle_seconds', 'turnout_seconds', 'travel_time_seconds']
    print(dataframe.groupby(status)[cols].median().T.round(1).to_string())

    for col in ['hour_of_day', 'day_of_week', 'home_station', 'station_area']:
        rate = dataframe.groupby(col)['is_kept'].agg(['mean', 'size'])
        print(f"\nkeep rate by {col}")
        print(rate.sort_values('mean').to_string())
##################################


def main():
    start_time = time.perf_counter()

    calls = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)

    calls = keep_code3_engines_first_dispatched(calls)

    calls['drop_reason'] = pd.Series(pd.NA, index = calls.index, dtype='string')

    calls = add_home_station(calls)
    calls = add_station_coords(calls)
    calls = keep_plausible_fromstation(calls)
    calls = keep_enough_idle_time(calls)
    calls = keep_straight_line_distance(calls)
    calls = keep_routed_distance(calls)
    calls = keep_plausible_speed(calls)


    calls['is_kept'] = calls['drop_reason'].isna()
    compare_kept_vs_dropped(calls)

    #calls.to_parquet(VARIABLES.GOOD_TRIPS_ALL_PARQ)
    #calls[calls['is_kept']].to_parquet(VARIABLES.GOOD_TRIPS_PARQ)

    end_time = time.perf_counter()
    print(f'total run time = {end_time - start_time}')

if __name__ == "__main__":
    main()
