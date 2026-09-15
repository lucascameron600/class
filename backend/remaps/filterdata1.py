import pandas as pd
import numpy as np
import geopandas as gpd
import VARIABLES
from shapely.geometry import Point
from shapely import wkt
import matplotlib.pyplot as plt
##currently set up for reading a CSV to end in a parquet. always ending in export parquet


#move to VARIABLES
MIN_TRAVEL_SECONDS = 20 #less than minutes
MAX_TRAVEL_SECONDS = 1400 # about 18.5 mins
PRIORITY_CODE = "3" #sf counts 3 as a code 3 emergency response


def data_printout(dataframe):
    print("Heres the data")
    print(dataframe.shape)
    print(dataframe.head(9).T)
    print(dataframe.dtypes) #strings
    p90 = dataframe["travel_time_seconds"].quantile(0.90)
    p50 = dataframe["travel_time_seconds"].quantile(0.50)
    p99 = dataframe["travel_time_seconds"].quantile(0.99)
    mean = dataframe["travel_time_seconds"].mean()
    print("p90:",p90, " p50:", p50, " p99:", p99, " mean:", mean)


##filters out, rename, and tag new columns
def filter_columns(dataframe):
    dataframe = dataframe.rename(columns=VARIABLES.MAP_CAD_COLUMNS)
    time_cols = ["dispatch_time", "enroute_time", "onscene_time", "transport_time", "available_time"]

    ##export data and time
    for column in time_cols:
        dataframe[column] = pd.to_datetime(dataframe[column], format="%Y %b %d %I:%M:%S %p")

    dataframe['travel_time_seconds'] = (dataframe['onscene_time'] - dataframe['enroute_time']).dt.total_seconds()

    shapley_column = gpd.GeoSeries.from_wkt(dataframe['call_location'])

    dataframe['call_longitude'] = shapley_column.x.values
    dataframe['call_latitude'] = shapley_column.y.values

    dataframe["hour_of_day"] = dataframe["enroute_time"].dt.hour
    dataframe["day_of_week"] = dataframe["enroute_time"].dt.dayofweek



    print('loaded calls fixed dates and extracted lat lon')
    return dataframe



#filters the dataframe for calls that are not helpful, we need starting at station going to the call code 3 must have all needed columns not na, and also excludes super short or long calls
def remove_unusable_calls(dataframe):
    starting_count = len(dataframe)

    get_enroute = dataframe['enroute_time'].notna()
    get_onscene = dataframe['onscene_time'].notna()

    get_lat = dataframe['call_latitude'].notna()
    get_lon = dataframe['call_longitude'].notna()

    get_realistic_fromstation_calls = ((dataframe['travel_time_seconds'] >= MIN_TRAVEL_SECONDS) & (dataframe['travel_time_seconds'] <= MAX_TRAVEL_SECONDS))

    ##get_p2 = dataframe["priority"].tostr() == "2"
    ##get_p1 = dataframe["priority"].tostr() == "1"

    #get_fire_laddertruck = dataframe
    get_code3 = dataframe['priority'].astype(str) == PRIORITY_CODE
    #get_p2 = dataframe['priority'].astype(str) == '2'

    calls_to_keep = (get_enroute & get_onscene & get_lat & get_lon & get_code3 & get_realistic_fromstation_calls)

    usable = dataframe[calls_to_keep].copy()
    print(f"started at {starting_count} rows")
    print(f"ended at {len(usable)} rows")

    return usable


def haversine(lat1, lon1, lat2, lon2):
    #series to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    deltalon = lon2 - lon1
    deltalat = lat2 - lat1

    a = np.sin(deltalat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(deltalon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000 # radius of earth in meters
    return c * r

##find good origins and then merge
def find_good_origins(incidents, stations):
    #group calls together, sort by time
    #calls line up in a row, take the previous availible time and subtract the current dispatch time,
    #that will make sure you are not accepting origins that are bad, only if the unit had a good amount of time
    #to get back to the station.


    incidents['station_id'] = incidents['unit_id'].str.extract(r'(\d+)').astype(int)

    incidents = incidents.merge(stations[['station_id', 'station_latitude', 'station_longitude']], on='station_id', how='left')
    incidents = incidents.sort_values(['unit_id', 'dispatch_time'])
    one_unit = incidents.groupby('unit_id', sort=False)

    #clever shift, cite this
    incidents["previous_call_latitude"] = one_unit["call_latitude"].shift(1)
    incidents["previous_call_longitude"] = one_unit["call_longitude"].shift(1)
    incidents["previous_call_available_time"] = one_unit["available_time"].shift(1)

    #incidents['turnaround_time'] = (

    incidents['turnaround_seconds'] = (incidents["dispatch_time"] - incidents["previous_call_available_time"]).dt.total_seconds()

    incidents['meters_to_station'] = haversine(incidents["previous_call_latitude"], incidents["previous_call_longitude"], incidents["station_latitude"], incidents["station_longitude"])

    ## take the time you had between the last availible, and the time you get your next call. if that would be too short to drive home in a straight line
    #at 7 m/s around 10mph disqualify
    had_time = incidents['turnaround_seconds'] * 3.0 > incidents['meters_to_station']
    #had_no_time = incidents['turnaround_seconds'] < 15

    trips = incidents[had_time].copy()
    ##
    ##if turnaround time < 10 seconds, use prev call lat and lon as origin
    ##
    trips["start_latitude"] = trips["station_latitude"]
    trips["start_longitude"] = trips["station_longitude"]



    trips["straight_line_meters"] = haversine(trips["start_latitude"], trips["start_longitude"],trips["call_latitude"], trips["call_longitude"])

    #filter for being too close to the call
    trips = trips[trips['straight_line_meters'] / trips['travel_time_seconds'] < 25].copy()


    return trips


def plot_usable_trips(df):

    fig, ax = plt.subplots(figsize=(12, 12), dpi=600)

    # call locations
    ax.scatter(df["call_longitude"], df["call_latitude"], s=2, c="blue", alpha=0.5, label="Calls")

    # inferred origins
    ax.scatter(df["start_longitude"], df["start_latitude"], s=12, c="red", alpha=0.5, label="Origins")

    ax.set_title("call locations and naive origins")
    ax.set_aspect("equal")   # keeps map from looking stretched
    ax.legend()

    plt.tight_layout()
    plt.savefig('call_and_origin.png', dpi=600)


def plot_distribution(df):
    fig, ax = plt.subplots(figsize=(12,12), dpi=600)

    ax.hist(df["travel_time_seconds"], bins=50)
    plt.savefig("travel_time_dist.png", dpi=600)




#def filter_good_station_origins(dataframe):
#    osrm_times = []
#
#    for i, row in dataframe.iterrows()
#        url = f"http://localhost:5000/route/v1/driving/{row['start_lon']},{row['start_lat']};{row['call_lon']},{row['end_lat']}?overview=false"





def main():
    df = pd.read_parquet(VARIABLES.RAW_CAD_FILE)
    sdf = pd.read_csv(VARIABLES.WORKING_STATIONS_CSV)
    df = filter_columns(df)

    engines = df[df['unit_type'] == 'ENGINE'].copy()
    trips = find_good_origins(engines, sdf)
    usable = remove_unusable_calls(trips)
    data_printout(usable)

    #plot_distribution(usable)

    plot_usable_trips(usable)
    #usable_fire_engines.to_parquet(VARIABLES.WORKING_CAD_PARQ)

if __name__ == '__main__':
    main()
