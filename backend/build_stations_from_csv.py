import pandas as pd
import geopandas as gpd
from backend import VARIABLES
from pathlib import Path





def filter_station_columns(dataframe):
    dataframe = dataframe.rename(columns=VARIABLES.MAP_STATION_COLUMNS)

    # only get number that follows station so non stations are NA
    extracted = dataframe['common_name'].str.extract(r'Station\s*#?\s*(\d+)', expand=False)
    dataframe['station_id'] = pd.to_numeric(extracted).astype('Int64')


    shapely_column = gpd.GeoSeries.from_wkt(dataframe['station_location'])
    dataframe['station_longitude'] = shapely_column.x.values
    dataframe['station_latitude'] = shapely_column.y.values


    # drop decomm fire station 21 and second station 7 building
    dataframe = dataframe[~dataframe['facility_id'].isin([1207, 732])].reset_index(drop=True)

    #manually adding station 51 here wasnt in my sf csv
    station_51 = pd.DataFrame({'common_name': ['Fire Station #51 (Presidio, added manually)'],'station_id': [51], 'station_longitude': [-122.45578], 'station_latitude': [37.80152]})
    dataframe = pd.concat([dataframe, station_51], ignore_index=True)

    dataframe['station_id'] = dataframe['station_id'].astype('Int64')
    print('loaded stations, filtered columns extracted lat long station_id')
    return dataframe



def main():
    stations_df = pd.read_csv(VARIABLES.RAW_STATIONS_CSV)
    filtered = filter_station_columns(stations_df)
    add_station_coords(filtered)
    #data_printout(filtered)
    filtered.describe()
    #impt_cols = ['common_name', 'facility_id', 'station_location']
    #dataframe = dataframe[impt_cols]


    filtered.to_parquet(VARIABLES.POST_ET_STATIONS_PARQ)
if __name__ == '__main__':
    main()
