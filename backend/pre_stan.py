#takes good_trips.parquet and cuts it down to the one table the stan model reads.


import numpy as np
import pandas as pd
import requests
from filterdata1 import data_printout

import VARIABLES


#move to VARIABLES later
#STAN_TABLE_CSV = STAN_TABLE_PARQ.with_suffix('.csv')

OSRM_ROUTE_URL = "http://localhost:5000/route/v1/driving"

osrm_sesh = requests.Session()

MODEL_COLUMNS = [
    ##ids
    'incident_id', 'unit_id', 'dispatch_time',


    #PREDICTORS/USABLE = travel_time_seconds, total_response_seconds, turnout_seconds, osrm_seconds, osrm_meters, station_index, time_bin


    ##filter file drops anything under MIN_TURNOUT_SECONDS

    'turnout_seconds', 'travel_time_seconds', 'total_response_seconds',

    #routed
    'osrm_seconds', 'osrm_meters',

    ##station effect. station_idx is 1 indexed no gaps
    'home_station', 'station_idx',


    'hour_of_day', 'day_of_week', 'time_bin',

    'gcd_meters',

    #uneeded
    'station_latitude', 'station_longitude', 'call_latitude', 'call_longitude',
]


def one_osrm_route(from_lat, from_lon, to_lat, to_lon):
    ##same request as the filter file. returns route meters and route seconds
    url = f"{OSRM_ROUTE_URL}/{from_lon},{from_lat};{to_lon},{to_lat}?overview=false"

    response = osrm_sesh.get(url, timeout=5).json()

    if response.get("code") != "Ok":
        return np.nan, np.nan

    route = response['routes'][0]
    return route['distance'], route['duration']


def add_osrm_route(trips):
    coordinates = ['station_latitude', 'station_longitude', 'call_latitude', 'call_longitude']
    unique_pairs = trips[coordinates].drop_duplicates().copy()
    print(f"routing {len(unique_pairs):,} pairs")

    routes = [one_osrm_route(*pair) for pair in unique_pairs.itertuples(index=False)]
    routes = pd.DataFrame(routes, columns=['osrm_meters', 'osrm_seconds'], index=unique_pairs.index)

    return trips.merge(unique_pairs.join(routes), on=coordinates, how='left', validate='many_to_one')


def main():
    trips = pd.read_parquet(VARIABLES.GOOD_TRIPS_PARQ)
    print(f"read {len(trips):,} good trips")

    #ROUTING
    trips = trips.rename(columns={'osrm_duration': 'osrm_seconds'})
    if 'osrm_seconds' not in trips.columns:
        trips = add_osrm_route(trips)

    has_route = trips['osrm_seconds'].gt(0)
    print(f"  dropped no osrm route      : {(~has_route).sum():,}")
    trips = trips[has_route].copy()
    #########################################



    #change to dispatch time
    trips['hour_of_day'] = trips['dispatch_time'].dt.hour.astype('int64')            #0 to 23
    trips['day_of_week'] = trips['dispatch_time'].dt.dayofweek.astype('int64')       #monday = 0


    #peak and off peak time bins
    hour = trips['hour_of_day']
    weekday = trips['day_of_week'] <= 4
    peak = weekday & (hour.between(6, 9) | hour.between(15, 18))    #6 to 10am and 3 to 7pm
    trips['time_bin'] = peak.astype('int64') + 1

    ##NO GAPS IN STATION NUMBERS
    trips['home_station'] = trips['home_station'].astype('int64')
    trips['station_idx'] = pd.factorize(trips['home_station'], sort=True)[0] + 1 #added one so no zero values

    table = trips[MODEL_COLUMNS].sort_values('dispatch_time').reset_index(drop=True)

    ##CHECK MISSING
    missing = table.isna().sum()
    if missing.any():
        print("  yo these columns still have missing values:")
        print(missing[missing > 0].to_string())

    data_printout(table)

    table.to_parquet(VARIABLES.STAN_TABLE_PARQ)
    #table.to_csv(MODEL_TABLE_CSV, index=False)
    print(f"wrote {VARIABLES.STAN_TABLE_PARQ} and stantable.csv ({len(table):,} rows, {table['station_idx'].nunique()} stations)")


if __name__ == '__main__':
    main()
