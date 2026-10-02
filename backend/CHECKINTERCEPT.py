import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

import VARIABLES

trips = pd.read_parquet(VARIABLES.GOOD_TRIPS_PARQ)

trips = trips[trips['travel_time_seconds'].between(1, VARIABLES.MAX_TRAVEL_SECONDS)]
trips = trips[trips['idle_seconds'] > 3600]


trips['kmph'] = (trips['gcd_meters'] / trips['travel_time_seconds']) * 3.6
trips['over_50'] = trips['kmph'] > 50
trips['under_5'] = trips['kmph'] < 5

trips = trips[~trips['over_50']]
trips = trips[~trips['under_5']]
meters = trips[['gcd_meters']]
seconds = trips['travel_time_seconds']



#plt.hist(trips['kmph'], bins = 8000)
#plt.axvline(trips['kmph'].median(), color='red')
#plt.axvline(trips['kmph'].mean(), color='tomato',linestyle='--')
#plt.xlim(0,300)


print(f'trips over 50{trips['over_50'].sum()}')


## SIMPLIFIED RAND USING GCD
## paper says erorr increases with distance!

model = LinearRegression().fit(meters, seconds)
log_error = np.log(seconds) - np.log(model.predict(meters))


print(f'\nlog rmse = {log_error.std()}')
print(f'y intercept = {model.intercept_} s')

print('\nKOLESAR/RAND simplified formula via NFPA T = 45 + 1.7D')

print(f'R^2 = {model.score(meters,seconds)}')
print(f'MODEL_SLOPE = {model.coef_}')

plt.scatter(meters,seconds,color='blue',s=.05)

plt.xlabel("meters")
plt.ylabel("seconds")

plt.savefig('hist.png', dpi=300)
plt.close()




