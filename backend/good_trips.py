#here, we take our cleaned trips, our cleaned stations, and then we combine them to build
#solid trips that we think are usable for prediction

##Already have idle_time_seconds

#GOAL: output a parquet that matches the trip population of map

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import VARIABLES

OSRM_URL = "http://localhost:5000" # OSRM SERVES HERE

# ALL DROP CRITERIA

MIN_STRAIGHT_METERS = 100      ##call is basically at the station or snapped to similar intersection
MIN_ROUTE_METERS = 400  #based on toronto paper adapted with OSRM

MIN_ROUTE_SPEED = 5
MAX_ROUTE_SPEED = 90




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

    add_home_station(calls)

    keep_code3_engines_first_dispatched(calls)

    keep_plausible_fromstation(calls)

    keep_straight_line_distance(calls)

    keep_routed_distance(calls)




if __name__ == "__main__":
    main()
