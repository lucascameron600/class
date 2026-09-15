import pandas as pd
import geopandas as gpd
import VARIABLES
from filterdata1 import data_printout
from pathlib import Path



def filter_station_columns(dataframe):
    dataframe = dataframe.rename(columns=VARIABLES.MAP_STATION_COLUMNS)

    dataframe['station_id'] = dataframe['common_name'].str.extract(r'(\d+)')

    shapley_column = gpd.GeoSeries.from_wkt(dataframe['station_location'])

    dataframe['station_longitude'] = shapley_column.x.values
    dataframe['station_latitude'] = shapley_column.y.values


    print('loaded stations, filtered columns extracted lat long station_id')
    return dataframe





def main():
    stations_df = pd.read_csv(VARIABLES.RAW_STATIONS_CSV)
    filtered = filter_station_columns(stations_df)
    data_printout(filtered)

    #impt_cols = ['common_name', 'facility_id', 'station_location']
    #dataframe = dataframe[impt_cols]


    filtered.to_csv(VARIABLES.WORKING_STATIONS_CSV)
if __name__ == '__main__':
    main()
