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
from filterdata1 import data_printout

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
    print(f"  dropped : {reason:<20}: {rows_to_drop.sum():,}")
    return dataframe


############################################################################
##################### MAIN FILTERS #########################################
############################################################################

def keep_has_travel_time(dataframe):
    mask = dataframe['travel_time_seconds'].notna()
    return flag_dropped(dataframe, mask, 'no_travel_time')

def keep_code3_engines_first_dispatched(dataframe):
    ##first dispatched only one trip per incident
    ## one engine leaving its station to the area of the call
    mask = dataframe['unit_type'].isin(['ENGINE']) & dataframe['is_code3']
    ## TODO: first dispatched
    return dataframe[mask].copy()


def keep_plausible_fromstation(dataframe):
    ## did this unit start at its station? according to exploratory visualization,
    ## a clean predictor of weather a unit is at station, is how fast the unit presses the button
    ## Westgate 2016 paper solved wtih gps map matching
    mask = dataframe['turnout_seconds'].between(MIN_TURNOUT_SECONDS, MAX_TURNOUT_SECONDS)

    return flag_dropped(dataframe, mask, ': turnout exclusion')


def keep_enough_idle_time(dataframe):
    return dataframe #INPROG


def keep_straight_line_distance(dataframe):
    ## drop calls that are within 400m GCD of the staion
    ## mostly noise based on toronto paper
    dataframe['gcd_meters'] = haversine(dataframe['station_latitude'], dataframe['station_longitude'], dataframe['call_latitude'], dataframe['call_longitude'])

    mask = dataframe['gcd_meters'] >= MIN_STRAIGHT_METERS

    return flag_dropped(dataframe, mask, ': 400 m straight line exclusion') #INPROG


def keep_routed_distance(dataframe):
    ## route call with osrm and see if it is over 400 meters, and
    return dataframe #INPROG


def keep_plausible_speed(dataframe):

    return dataframe #INPROG


######## REPLACE ME #################################

def check_bias(dataframe, station):
    # check how much our filters bias the travel times at the 90th percentiles
    # if large bias, could shape the way the map is drawn at 90th

    call_hour = dataframe['received_time'].dt.floor('h')
    dataframe['calls_that_hour'] = (dataframe.groupby(['station_area', call_hour])['incident_id'].transform('size')) #calc num rows

    one_station = dataframe[dataframe['home_station'].eq(station)].copy()

    call_volume_rank = one_station['calls_that_hour'].rank(method='first')

    one_station['call_volume'] = pd.qcut(call_volume_rank, 4, labels=['least call volume', 'medium call volume', 'high call volume', 'very high call volume'])
    print(f"\nstation {station} keep rate by call volume")
    print(f'-------------------------------------------')

    keep_rate = (one_station.groupby('call_volume', observed=True)['is_kept'].mean())
    print(keep_rate.to_string())
    print(f'-------------------------------------------')

    print(f"\nstation {station} kept 90th percentile travel time by call volume")
    print(f'-------------------------------------------')

    kept = one_station[one_station['is_kept']]

    travel_p90 = (kept.groupby('call_volume', observed = True)['travel_time_seconds'].quantile(.9))
    print(travel_p90.to_string())
    print(f'-------------------------------------------')

    return dataframe

def turnout_sweep(dataframe, stations=(1, 3, 36, 35, 5)):
    ## how do travel times change as the minimum turnout turnout cuttof goes up
    results = []

    for cutoff in [0, 5, 10, 15, 20, 25, 30, 40]:
        ok = dataframe['turnout_seconds'].between(cutoff, MAX_TURNOUT_SECONDS, inclusive='left')
        kept = dataframe[ok]
        row = {'cutoff': cutoff, 'kept_share': ok.mean(), 'median': kept['travel_time_seconds'].median(),'p90': kept['travel_time_seconds'].quantile(0.9)}


        for s in stations:
            row[f'p90_st{s}'] = kept.loc[kept['home_station'].eq(s), 'travel_time_seconds'].quantile(0.9)

        results.append(row)
    print('-----------------------------------------------------')
    print(pd.DataFrame(results).round(2).to_string(index=False))
    print('-----------------------------------------------------')
##################################


def main():
    start_time = time.perf_counter()

    calls = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)

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

    calls['is_kept'] = calls['drop_reason'].isna()
    ################################################

    check_bias(calls, station=3)
    turnout_sweep(calls)

    total = len(calls)
    kept = calls['is_kept'].sum()
    print(f"total code 3 engine trips quote from station unquote: {total:,}")
    print(f"kept:        {kept:,} ({kept / total:.1%})")
    print(f"dropped:     {total - kept:,} ({(total - kept) / total:.1%})")
    #######################################################
    #calls.to_parquet(VARIABLES.GOOD_TRIPS_ALL_PARQ)
    #calls[calls['is_kept']].to_parquet(VARIABLES.GOOD_TRIPS_PARQ)

    end_time = time.perf_counter()
    print(f'total run time = {end_time - start_time}')

if __name__ == "__main__":
    main()
