#all settings for data ingestion here

from pathlib import Path


RAW_CAD_FILE = Path('../data/workingfiles/cad/raw_sf_cad.parquet')
RAW_STATIONS_CSV = Path('../data/sf_fire_stations.csv')


WORKING_CAD_PARQ = Path('../data/workingfiles/cad/working_sf_cad.parquet')
WORKING_STATIONS_CSV = Path("../data/workingfiles/stations/working_sf_stations.csv")


MAP_CAD_COLUMNS = {
    "Call Number":            "call_id",
    "Unit ID":                "unit_id",
    "Unit Type":              "unit_type",
    "Call Type":              "call_type",
    "Original Priority":      "original_priority", #originally dispatched priority 3
    "Final Priority":         "final_priority",    #
    "Priority":               "priority",
    "Call Final Disposition": "final_disposition",
    "Response DtTm":          "enroute_time",     # SF response is en route time
    "On Scene DtTm":          "onscene_time",
    "Dispatch DtTm":          "dispatch_time", #when were they dispatched? turnout = ER - dispatchtime
    "Transport DtTm":         "transport_time",
    "Available DtTm":         "available_time",
    "case_location":          "call_location",         # coords in degrees of lon lat [lon, lat]
}

MAP_STATION_COLUMNS = {
    'geom':             "station_location"

}
