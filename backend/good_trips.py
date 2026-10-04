#here, take our cleaned trips, our cleaned stations, and then we combine them to build
#solid trips that we think are usable for prediction

#POPULATION = engine only, code 3, not upgraded, responding inside their first due area(excludes majority of move ups)

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
from filterdata1 import data_printout


import VARIABLES


osrm_sesh = requests.Session()

############################################################################
############ ALL DROP CRITERIA #############################################
############################################################################

# predictor of on road status, unit presses button quickly
# means they were likely in vehicle
# this is a judgement call, based on visaulaizaion of data
#need to tell stan
MIN_TURNOUT_SECONDS = 20
MAX_TURNOUT_SECONDS = 600


#need sweep
MIN_IDLE_TIME = 600

#based on the paper, catches real close calls
MIN_STRAIGHT_METERS = 100
MAX_STRAIGHT_METERS = 8000
# extra catch for short travel times

#WILL USE #NEED SWEEP
MIN_ROUTE_METERS = 150

#not sure about this yet
MAX_DETOUR_RATIO = None #TODO

# loosley based on paper,
# have to exclude only outlier time segments
# designed to be loose cutoffs to mitigate losing data
# remove any real data

MIN_ROUTE_SPEED = 1
MAX_ROUTE_SPEED = 90

MAX_TRAVEL_SECONDS = 30 * 60


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


#complicated join
def add_station_coords(dataframe):
    stations = pd.read_parquet(VARIABLES.POST_ET_STATIONS_PARQ).dropna(subset=['station_id'])

    stations = stations.rename(columns={'station_id': 'home_station'})
    stations['home_station'] = pd.to_numeric(stations['home_station']).astype('Int64')
    stations = stations[['home_station', 'station_latitude', 'station_longitude']]

    dataframe = dataframe.merge(stations, on='home_station', how='left', validate='many_to_one')
    return flag_dropped(dataframe, dataframe['station_latitude'].notna(), 'no_station_coords')


def flag_dropped(dataframe, keep_mask, reason):
    keep_mask = keep_mask.fillna(False).astype(bool)
    dataframe[f'pass_{reason}'] = keep_mask

    rows_to_drop = ~keep_mask & dataframe['drop_reason'].isna()
    dataframe['drop_reason'] = dataframe['drop_reason'].mask(rows_to_drop, reason)
    print(f'----------------------------------------------')
    print(f"  dropped : {reason:<20}: {rows_to_drop.sum():,}")
    print(f'----------------------------------------------')
    return dataframe


############################################################################
##################### MAIN FILTERS #########################################
############################################################################

def keep_has_travel_time(dataframe):
    mask = dataframe['travel_time_seconds'].notna()
    return flag_dropped(dataframe, mask, 'no_travel_time')

def keep_not_upgrade(dataframe):
    #calls upgraded on the way started without lights and sirens
    #biases times slow
    #TODOTODO make sure toher emergent priorities arent excluded
    mask = dataframe['original_priority'].isin(['2']) & dataframe['final_priority'].isin(['3'])
    return flag_dropped(dataframe, ~mask, 'upgraded_on_the_way')


def keep_code3_engines_first_dispatched(dataframe):
    ## first arrived?? gonna include all
    ## one engine leaving its station code 3 to the area of the call
    mask = dataframe['unit_type'].isin(['ENGINE']) & dataframe['is_code3']
    ## TODO: first dispatched
    return dataframe[mask].copy()


def keep_plausible_fromstation(dataframe):
    ## did this unit start at its station? according to exploratory visualization,
    ## a clean predictor of weather a unit is at station, is how fast the unit presses the button
    ## Westgate 2016 paper solved wtih gps map matching
    mask = dataframe['turnout_seconds'].ge(MIN_TURNOUT_SECONDS)

    return flag_dropped(dataframe, mask, 'turnout')


def keep_not_call_box(dataframe):
    ## call box addresses are placeholders so distance to them isnt real
    is_box = dataframe['Address'].astype('string').str.upper().str.startswith('CALL BOX').fillna(False)
    return flag_dropped(dataframe, ~is_box, 'call_box')


def keep_not_late_press(dataframe):
    ## crew pressed on scene as they cleared long after really arriving
    gap  = (dataframe['available_time'] - dataframe['onscene_time']).dt.total_seconds()
    kmph = dataframe['gcd_meters'] / dataframe['travel_time_seconds'] * 3.6
    late = (gap < 60) & (kmph < 7) & (dataframe['travel_time_seconds'] > 300)
    return flag_dropped(dataframe, ~late, 'late_press')

#NEED SWEEP
def keep_enough_idle_time(dataframe):
    return dataframe #INPROG


def keep_straight_line_distance(dataframe):
    ## drop calls that are within 400m GCD of the staion
    ## mostly noise based on toronto paper
    dataframe['gcd_meters'] = haversine(dataframe['station_latitude'], dataframe['station_longitude'], dataframe['call_latitude'], dataframe['call_longitude'])

    mask = dataframe['gcd_meters'] >= MIN_STRAIGHT_METERS
    mask &= dataframe['gcd_meters'] <= MAX_STRAIGHT_METERS

    return flag_dropped(dataframe, mask, 'straight_line_exclusion') #INPROG


def keep_first_due_area(dataframe):
    ## engines covering another station (move ups) respond in that station's area, not their own
    mask = pd.to_numeric(dataframe['station_area'], errors='coerce') == dataframe['home_station']
    return flag_dropped(dataframe, mask, 'not_first_due_area')


def keep_routed_distance(dataframe):
    ## route call with osrm and see if it is over 400 meters, and
    return dataframe #INPROG


def keep_plausible_speed(dataframe):

    return dataframe #INPROG


######## REPLACE ME #################################


def turnout_sweep(dataframe, stations=(1, 3, 36, 35, 5)):
    ## how do travel times change as the minimum turnout turnout cuttof goes up
    dataframe = dataframe[dataframe['pass_no_station_coords'] & dataframe['pass_no_travel_time'] & dataframe['pass_straight_line_exclusion']]
    results = []

    for cutoff in [0, 5, 10, 15, 20, 25, 30, 40]:
        ok = dataframe['turnout_seconds'].ge(cutoff)
        kept = dataframe[ok]
        row = {'cutoff': cutoff, 'kept_share': ok.mean(), 'median': kept['travel_time_seconds'].median(),'p90': kept['travel_time_seconds'].quantile(0.9)}


        for s in stations:
            station_travel = kept.loc[kept['home_station'].eq(s), 'travel_time_seconds']

            #row[f'n_st{s}'] = station_travel.count()
            row[f'p90_st{s}'] = station_travel.quantile(0.9)
        results.append(row)
    print('\n------------- TURNOUT CUTOFF SWEEP ------------------------------------')
    print(pd.DataFrame(results).round(2).to_string(index=False))
    print('-------------------------------------------------------------------------')
##################################


def main():
    start_time = time.perf_counter()

    calls = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)

    #KEEP ONLY CODE 3
    calls = keep_code3_engines_first_dispatched(calls)
    calls['drop_reason'] = pd.Series(pd.NA, index = calls.index, dtype='string')

    ######################################################################
    calls = add_home_station(calls)

    calls = add_station_coords(calls)
    ## toronto paper excludes those with no travel times, never explicitly stated, but cant measure travel time without it
    ## would have to estimate where the unit was at to include a travel time
    calls = keep_has_travel_time(calls)

    calls = keep_plausible_fromstation(calls)
    calls = keep_enough_idle_time(calls)
    calls = keep_straight_line_distance(calls)
    calls = keep_routed_distance(calls)
    calls = keep_plausible_speed(calls)
    calls = keep_not_late_press(calls)
    calls = keep_not_call_box(calls)
    #calls = keep_first_due_area(calls)

    calls = keep_not_upgrade(calls)

    calls['is_kept'] = calls['drop_reason'].isna()
    ################################################

    #check_bias(calls, station=5)
    turnout_sweep(calls)

    total = len(calls)
    kept = calls['is_kept'].sum()
    print(f"total code 3 engine trips quote from station unquote: {total:,}")
    print(f"kept:        {kept:,} ({kept / total:.1%})")
    print(f"dropped:     {total - kept:,} ({(total - kept) / total:.1%})")
    #######################################################
    #calls.to_parquet(VARIABLES.GOOD_TRIPS_ALL_PARQ)
    calls[calls['is_kept']].to_parquet(VARIABLES.GOOD_TRIPS_PARQ)

    end_time = time.perf_counter()
    print(f'total run time = {end_time - start_time}')

if __name__ == "__main__":
    main()
