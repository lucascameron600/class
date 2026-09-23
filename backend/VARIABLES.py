#all settings for data ingestion here.



from pathlib import Path


RAW_CAD_FILE = Path('../data/workingfiles/cad/raw_sf_cad.parquet')
RAW_STATIONS_CSV = Path('data/sf_fire_stations.csv')


POST_ET_CAD_PARQ = Path('../data/workingfiles/cad/post_etl_sf_cad.parquet')
POST_ET_STATIONS_PARQ = Path("data/workingfiles/stations/working_sf_parq.parqet")


FIGURE_DIR = Path('../data/workingfiles/figures')


MAP_CAD_COLUMNS = {
    "Call Number":            "call_id", #each call unique from 911 so we use incident number
    "Incident Number":        "incident_id",   # I believe call and incident number are similar
    "Unit ID":                "unit_id",
    "Unit Type":              "unit_type",
    "Call Type":              "call_type",
    "Call Type Group":        "call_type_group",
    "Original Priority":      "original_priority", #originally dispatched priority 3
    "Final Priority":         "final_priority",    #
    "Priority":               "priority",
    "Call Final Disposition": "final_disposition",
    "Received DtTm":          "received_time",    # 911 answered
    "Entry DtTm":             "entry_time",       # call taker finished entering it
    "Dispatch DtTm":          "dispatch_time", #when were they dispatched? turnout = ER - dispatchtime
    "Response DtTm":          "enroute_time",     # SF response is en route time
    "On Scene DtTm":          "onscene_time",
    "Transport DtTm":         "transport_time",
    "Hospital DtTm":          "hospital_time",   #Unit arrived at the hospital
    "Available DtTm":         "available_time",
    "Station Area":           "station_area",     # SF's own first-due district. the unit of SOC reporting
    "Battalion":              "battalion",
    "ALS Unit":               "als_unit",
    "Number of Alarms":       "number_of_alarms",
    "Unit sequence in call dispatch": "dispatch_sequence",
    "case_location":          "call_location",         # coords in degrees of lon lat [lon, lat]
}

MAP_STATION_COLUMNS = {
    'geom':             "station_location"

}

# the CAD export writes timestamps like "2024 Jan 05 07:53:21 PM"
CAD_DATETIME_FORMAT = "%Y %b %d %I:%M:%S %p"

# every duration we measure, as (name, start column, end column).
TIME_INTERVALS = [
    ("alarm_handling_seconds",  "received_time", "dispatch_time"),  # 911 pickup -> units dispatched
    ("turnout_seconds",         "dispatch_time", "enroute_time"),   # dispatched -> wheels rolling
    ("travel_time_seconds",     "enroute_time",  "onscene_time"),   # rolling -> on scene
    ("total_response_seconds",  "dispatch_time", "onscene_time"),   # turnout + travel
    ("response_from_alarm_seconds", "received_time", "onscene_time"),  # what the caller experiences
    ("commit_seconds",          "dispatch_time", "available_time"), # how long the unit was tied up
]

# ---- data validity checks --------------------
# These reject impossible records (clock errors, units marked on scene by a
# supervisor hours later). They are NOT performance filters
MAX_ALARM_HANDLING_SECONDS = 30 * 60
MAX_TURNOUT_SECONDS        = 30 * 60
MAX_TRAVEL_SECONDS         = 30 * 60
MAX_COMMIT_SECONDS         = 24 * 60 * 60

# ---- origin inference (moving to the next file) ---------------------------
ORIGIN_MIN_TRAVEL_SECONDS = 20      # below this the unit was already on/next to the call
ORIGIN_MAX_TRAVEL_SECONDS = 1400    # about 18.5 mins
ORIGIN_RETURN_SPEED_MPS = 3.0       # assumed speed getting back to quarters, ~7 mph
ORIGIN_MAX_IMPLIED_SPEED_MPS = 25.0 # straight-line speed above this means a bad origin

# origin inference output (find_origins.py)
WORKING_TRIPS_PARQ = Path("../data/workingfiles/cad/station_origin_trips.parquet")

#unit type catagories
ALL_FIRE_UNITS = ['INVESTIGATION', 'AIRPORT', 'MEDIC', 'SUPPORT', 'CHIEF', 'CP', 'ENGINE', 'TRUCK', 'RESCUE SQUAD', 'RESCUE CAPTAIN']
SUPPRESSION_UNITS = ['ENGINE', 'TRUCK']
TRANSPORT_UNITS = ['MEDIC', 'PRIVATE']  #PRIVATE is the only non fire unit
PRIVATE_UNITS = ['PRIVATE']
COMMAND_UNITS = ['CP', 'CHIEF']
