import json

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from filterdata1 import data_printout
import cmdstanpy


import VARIABLES



def main():

    table = pd.read_parquet(VARIABLES.STAN_TABLE_PARQ)

    data_printout(table)


    station_idx, station_ids = pd.factorize(table['home_station'], sort=True)

    stan = {
            "N": len(table),
            "x": table['osrm_meters'].to_numpy(),
            "y": table['total_response_seconds'].to_numpy(),

            "S": len(station_ids),
            "station": station_idx + 1,

            "night": ((table['hour_of_day'] >= 22) | (table['hour_of_day'] < 6)).astype(int).to_numpy(),
            }

    cmdstanpy.write_stan_json('stan/regression.json', stan)


    ##NEW
    # so that each station can be mapped back after it is fit.
    station_lookup = {}
    stan_index = 1

    for station_id in station_ids:
        station_lookup[stan_index] = int(station_id)
        stan_index += 1

    lookup_path = Path("stan") / "station_lookup.json"
    lookup_path.write_text(json.dumps(station_lookup, indent=2))

    print(f"Wrote {len(station_lookup)} stations to {lookup_path}")


if __name__ == '__main__':
    main()
