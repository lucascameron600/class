import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

import VARIABLES

trips = pd.read_parquet(VARIABLES.GOOD_TRIPS_PARQ)
trips = trips[trips['travel_time_seconds'].between(1, VARIABLES.MAX_TRAVEL_SECONDS)]
trips = trips[trips['idle_seconds'] > 3600]

meters = trips[['gcd_meters']]
seconds = trips['travel_time_seconds']

## SIMPLIFIED RAND USING GCD
model = LinearRegression().fit(meters, seconds)
log_error = np.log(seconds) - np.log(model.predict(meters))


print(f'\nlog rmse = {log_error.std()}')
print(f'y intercept = {model.intercept_} s')

print('\nKOLESAR/RAND simplified formula via NFPA T = 45 + 1.7D')




