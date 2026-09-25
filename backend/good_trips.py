#here, we take our cleaned trips, our cleaned stations, and then we combine them to build
#solid trips that we think are usable for prediction


import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import VARIABLES


MIN_IDLE_MINUTES = 30          ##available this long before dispatch -> assume it left from quarters
MIN_TRAVEL_SECONDS = 30
MAX_TRAVEL_SECONDS = 20 * 60
MIN_STRAIGHT_METERS = 100      ##call is basically at the station travel time
MIN_STRAIGHT_KMH = 5           ##straight line speed, the real route is always longer than this
MAX_STRAIGHT_KMH = 110


def main():
    start_time = time.perf_counter()

    calls = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)



if __name__ == "__main__":
    main()
