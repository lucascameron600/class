import pandas as pd
import geopandas as gpd
import VARIABLES
import time

##reads the raw CAD parquet, normalizes it, flags it, and exports a parquet.
##this file only drops rows that are useless or impossible
#move to VARIABLES later

PRIORITY_COLUMN = "final_priority"  #sf final priority is the 2 or 3 that says emergency or no emergency
EMERGENT_PRIORITY_CODES = ["3"]                 #sf counts P3 as a code 3 emergency response
#NON_EMERGENT_PRIORITY_CODES = ["2", "1", "A"]

##cad data come in as text or numbers depending on the export.
##  " E10" -> "E10"   10.0 -> "10"
##astype(str) on a float column gives 3.0 which matches nothing
def normalize_code(series):
    series = series.astype("string").str.strip().str.upper()
    series = series.str.replace(r"\.0$", "", regex=True)
    return series.where(series.str.len() > 0, other=pd.NA)


##pull the lon lat out of the point column
def extract_points(wkt_series):
    cleaned = wkt_series.astype("string").str.strip()
    cleaned = cleaned.where(cleaned.str.len() > 0, other=pd.NA)
    points = gpd.GeoSeries.from_wkt(cleaned, on_invalid="ignore")
    return points.x.values, points.y.values

#____________________________________
##filters out, rename, and tag new columns
def filter_columns(dataframe):
    dataframe = dataframe.rename(columns=VARIABLES.MAP_CAD_COLUMNS).reset_index(drop=True) #No-op did because originally was a after another one

    ##export date and time
    time_cols = ["received_time", "dispatch_time", "enroute_time", "onscene_time","transport_time", "available_time"]

    for column in time_cols:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], format=VARIABLES.CAD_DATETIME_FORMAT, errors="coerce")

    ##clean up the code columns so they compare properly
    for column in ["priority", "original_priority", "final_priority", "station_area"]:
        if column in dataframe.columns:
            dataframe[column] = normalize_code(dataframe[column])

    if 'call_location' in dataframe.columns:
        dataframe['call_longitude'], dataframe['call_latitude'] = extract_points(dataframe['call_location'])

    #NFPA time interval in seconds
    for name, start, end in VARIABLES.TIME_INTERVALS:
        dataframe[name] = (dataframe[end] - dataframe[start]).dt.total_seconds()


    ##grouping based off when the call was received. Need recieved time to be usable
    dataframe["hour_of_day"] = dataframe["received_time"].dt.hour.astype('int64')
    dataframe["day_of_week"] = dataframe["received_time"].dt.dayofweek.astype('int64')

    print('loaded calls fixed dates and extracted lat lon')
    return dataframe

#_________________________________________________________
def flag_unit_types(dataframe):
    dataframe['is_fire'] = dataframe['unit_type'].isin(VARIABLES.ALL_FIRE_UNITS)
    dataframe['is_command'] = dataframe['unit_type'].isin(VARIABLES.COMMAND_UNITS)
    dataframe['is_transport'] = dataframe['unit_type'].isin(VARIABLES.TRANSPORT_UNITS)
    dataframe['is_suppression'] = dataframe['unit_type'].isin(VARIABLES.SUPPRESSION_UNITS)
    dataframe['is_private'] = dataframe['unit_type'].isin(VARIABLES.PRIVATE_UNITS)

    ##anything that landed in no group is unaccounted for unit_type
    unknown = dataframe[~dataframe['is_fire'] & ~dataframe['is_command'] & ~dataframe['is_transport']]
    if len(unknown) > 0:
        print(f"  yo {len(unknown)} rows are not is_fire or is_command or is_transport:")
        print(unknown['unit_type'].value_counts().head(10))

    print(f"fire rows: {dataframe['is_fire'].sum():,} of {len(dataframe):,}")
    return dataframe


##emergency response or not
def flag_code3(dataframe):
    series = dataframe[PRIORITY_COLUMN]
    dataframe['is_code3'] = series.isin(EMERGENT_PRIORITY_CODES).to_numpy(dtype=bool)
    dataframe['is_code2'] = series.isin(['2', '1']).to_numpy(dtype=bool)
    #dataframe['is_code3'] = dataframe[PRIORITY_COLUMN] == PRIORITY_CODE
    n = len(dataframe)
    other = n - dataframe['is_code3'].sum() - dataframe['is_code2'].sum()

    print(f"code 3 rows: {dataframe['is_code3'].sum():,} of {len(dataframe):,}, code 2 rows: {dataframe['is_code2'].sum():,} other {other}")
    return dataframe


##this is more cancelled after call received,
def flag_cancelled(dataframe):
    dataframe['is_cancelled_en_route'] = (dataframe['dispatch_time'].notna()
                                       & dataframe['onscene_time'].isna())
    print(f"{dataframe['is_cancelled_en_route'].sum()} :units got cancelled en route")
    return dataframe


#def flag_medic_available():



#def flag_

#NEXT


#def flag_response_in_first_due():

#outside its own station area for a response, (longer times dont count for response time calculation)
#def flag_mutual_aid_fire(dataframe):
#    try:
#        ##add is_command maybe. what is their station area?
#        dataframe['is_mutual_aid'] = dataframe['is_fire'].notna() & dataframe['station_area'] ==
#    except:
#        print('yo somethings up')


##rank who got to the call first, over ALL units.
##this has to happen before anything is dropped. if you drop the medic first then
##the engine looks like it was first when really the medic beat it there.
##soc.py re-ranks inside its own population, this one is just descriptive.

## memory killer
def flag_arrival_order(dataframe):
    print(f"length before flagging arrival{len(dataframe)}")
    dataframe = dataframe.sort_values(['incident_id', 'onscene_time'])

    arrived = dataframe['onscene_time'].notna()
    dataframe['arrival_rank_all'] = dataframe[arrived].groupby('incident_id').cumcount() + 1

    one_call = dataframe.groupby('incident_id')
    dataframe['units_on_incident'] = one_call['unit_id'].transform('size')
    dataframe['units_arrived_on_incident'] = one_call['arrival_rank_all'].transform('max').fillna(0).astype('int64')

    ##what kind of unit actually got there first
    first_rows = dataframe[dataframe['arrival_rank_all'] == 1]
    first_types = first_rows.set_index('incident_id')['unit_type']
    dataframe['first_unit_type'] = dataframe['incident_id'].map(first_types)

    ##did a fire unit respond at all, and did ems beat them there
    dataframe['fire_responded'] = one_call['is_fire'].transform('any')  #what???
    dataframe['suppression_beaten_by_ems'] = (dataframe['first_unit_type'].notna() & ~dataframe['first_unit_type'].isin(VARIABLES.SUPPRESSION_UNITS))

    print(f"flagged arrival order over all units now have {len(dataframe)}")
    return dataframe




#memory killer
def remove_unusable_calls(dataframe):

    get_not_duplicate = ~dataframe.duplicated(subset=["incident_id", "unit_id", "dispatch_time"], keep="first")

    get_dispatch = dataframe['dispatch_time'].notna()
    get_location = dataframe['call_latitude'].notna() & dataframe['call_longitude'].notna()

    #negative interval is not good
    #move this to flag
    alarm = dataframe['alarm_handling_seconds']
    turnout = dataframe['turnout_seconds']
    travel = dataframe['travel_time_seconds']
    commit = dataframe['commit_seconds']
    total = dataframe['total_response_seconds']
    from_alarm = dataframe['response_from_alarm_seconds']


    get_first_arrivers = dataframe['arrival_rank_all'].eq(1)
    get_suppression_units = dataframe ['is_suppression']
    get_fire_units = dataframe['is_fire']
    get_transport_units = dataframe['is_transport']
    get_private_units = dataframe['is_private']

    get_code3 = dataframe['is_code3']

    #only non negative intervals possibly calls get in with negative intervals. could be timezone differences
    get_alarm_ok = alarm.ge(0) | alarm.isna()
    get_turnout_ok = turnout.ge(0)| turnout.isna()
    get_travel_ok = travel.between(1,2000) | travel.isna()
    get_commit_ok = commit.ge(0) | commit.isna()
    get_total_ok = total.ge(0) | total.isna()
    get_from_alarm_ok = from_alarm.ge(0) | from_alarm.isna()

    ##these counts overlap, one bad row can fail two rules, so they do not add up
    ##to the total dropped. they tell you which rule is doing the work
    #print(f"started at {starting_count} rows")
    print(f"  duplicate row      : {(~get_not_duplicate).sum():,}")
    print(f"  no dispatch time   : {(~get_dispatch).sum():,}")
    print(f"  no location        : {(~get_location).sum():,}")
    print(f"  bad alarm handling : {(~get_alarm_ok).sum():,}")
    print(f"  bad turnout        : {(~get_turnout_ok).sum():,}")
    print(f"  bad travel         : {(~get_travel_ok).sum():,}")
    print(f"  bad commit         : {(~get_commit_ok).sum():,}")
    print(f"  bad responseseconds : {(~get_total_ok).sum():,}")
    print(f"  bad responsefrmalarm : {(~get_from_alarm_ok).sum():,}")
    print(f"  is cancelled during response?: {(dataframe['is_cancelled_en_route']).sum()}, ")
    print(f"  this many first arrivers: {len(get_first_arrivers)}")
    print(f"  this many suppression: {len(get_suppression_units)}")
    print(f"  transport units included:    {(get_transport_units).sum():,}")
    calls_to_keep = (get_not_duplicate & get_dispatch & get_location & get_travel_ok
                     & get_turnout_ok & get_commit_ok & get_alarm_ok & get_total_ok
                     & get_from_alarm_ok)

    #usable = dataframe[calls_to_keep].copy()
    #print(f"ended at {len(usable)} rows ({len(usable) / starting_count:.1%} of input)")
    return dataframe[calls_to_keep]

#___________________________________________________________________________________
##cut down to a study period. both ends are inclusive so end="2019-05-31" keeps
##everything that happened on may 31st

def keep_dates(dataframe, start_date=None, end_date=None): #yyyy-mm-dd

    timestamps = dataframe['received_time']
    keep = timestamps.notna()
    n_missing = (~keep).sum()

    if start_date is not None:
        keep &= (timestamps >= pd.Timestamp(start_date))
    if end_date is not None:
        keep &= (timestamps < pd.Timestamp(end_date) + pd.Timedelta(days=1))

    windowed = dataframe[keep].copy()

    print(f"date window {start_date} to {end_date} kept {len(windowed):,} of {len(dataframe):,} rows")
    if n_missing:
        print(f"  {n_missing:,} rows dropped for missing/NaT received_time")

    return windowed





def data_printout(dataframe):
    print("Heres the data")
    print(dataframe.shape)
    print(dataframe.head(9).T)
    print(dataframe.dtypes) #strings
    print(dataframe.describe().T)


def main():
    start_time = time.perf_counter()

    dataframe = pd.read_parquet(VARIABLES.RAW_CAD_FILE)
    start_len = len(dataframe)

    dataframe = filter_columns(dataframe)

    dataframe = keep_dates(dataframe, start_date='2018-01-01', end_date='2023-01-02')
    #print(sorted(dataframe['station_area'].dropna().unique()))

    dataframe = flag_cancelled(dataframe)
    dataframe = flag_unit_types(dataframe)
    dataframe = flag_code3(dataframe)
    dataframe = flag_arrival_order(dataframe)
    #print(dataframe['original_priority'].unique())

    print("CLEANING")
    clean = remove_unusable_calls(dataframe)

    ###NOTES
    #als_unit is still str holding 'true'/'false',
    #and number_of_alarms/dispatch_sequence are still str when they're numeric. FIX THIS
    #need to add in area first due responses
    #need to add medic at hospital flag per transport unit call
    #

    data_printout(clean)

    #plot_mult_hist(dataframe, title="response_intervals")
    #kde_sidebyside_vis_covid(clean, "all transport unit", "SF Transporting Units")
    #plot_mult_hist(clean, "Response Intervals all transport unit")
    #plot_hist(clean['travel_time_seconds'], "Travel Time Seconds")
    end_time = time.perf_counter()
    total_prog_time = end_time - start_time

    print(f"started at {start_len} ended at {len(clean)}")
    print(f"total program time {int(total_prog_time)} seconds")
    VARIABLES.POST_ET_CAD_PARQ.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(VARIABLES.POST_ET_CAD_PARQ)
    print(f"wrote {VARIABLES.POST_ET_CAD_PARQ} ({len(clean):,} rows)")


if __name__ == '__main__':
    main()
