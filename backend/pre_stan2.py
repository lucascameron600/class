import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from filterdata1 import data_printout
import cmdstanpy


import VARIABLES



def main():

    table = pd.read_parquet(VARIABLES.STAN_TABLE_PARQ)

    data_printout(table)

    # Stan needs stations as 1..S. factorize gives 0..S-1 plus the station number for each code
    station_idx, station_ids = pd.factorize(table['home_station'], sort=True)
    if (station_idx < 0).any():
        raise ValueError(f"{(station_idx < 0).sum()} rows have no home_station, drop them first")

    stan = {
            "N": len(table),
            "x": table['osrm_meters'].to_numpy(),
            "y": table['total_response_seconds'].to_numpy(),
            "S": len(station_ids),
            "station": station_idx + 1,
            }

    cmdstanpy.write_stan_json('stan/regression.json', stan)

    # so u[k] in the fit can be mapped back to a real station number
    with open('stan/station_lookup.json', 'w') as f:
        json.dump([int(s) for s in station_ids], f)
    print(f"{len(station_ids)} stations written to stan/station_lookup.json")

if __name__ == '__main__':
    main()
