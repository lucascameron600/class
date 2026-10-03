import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import VARIABLES

trips = pd.read_parquet(VARIABLES.GOOD_TRIPS_PARQ)

trips = trips[trips['total_response_seconds'].between(1, VARIABLES.MAX_TRAVEL_SECONDS)]
trips = trips[trips['idle_seconds'] > 3600]


trips['kmph'] = (trips['gcd_meters'] / trips['travel_time_seconds']) * 3.6


###############################
def p90_by_distance(trips):
    ## 90th percentile of the outcome for calls about 0.5, 1 and 2 km away in a straight line
    bands = [(400, 600), (900, 1100), (1900, 2100)]
    return [trips.loc[trips['gcd_meters'].between(low, high), 'total_response_seconds'].quantile(0.9) for low, high in bands]

def show(label, kept):
    near, mid, far = p90_by_distance(kept)
    print(f'{label:<22} {len(kept):>8,}   {near:>6.0f} {mid:>6.0f} {far:>6.0f}')

print('\nfilter                 trips kept   p90 at 0.5, 1, 2 km (s)')
show('no speed filter', trips)
for slow in [0, 1, 2, 3, 5, 7, 10]:
    show(f'drop under {slow} km/h', trips[trips['kmph'] >= slow])

for fast in [90, 70, 50, 40]:
    show(f'drop over {fast} km/h', trips[trips['kmph'] <= fast])
###################################3


trips['over_50'] = trips['kmph'] > 100
trips['under_5'] = trips['kmph'] < 5

trips = trips[~trips['over_50']]
trips = trips[~trips['under_5']]

meters = trips[['gcd_meters']]
seconds = trips['total_response_seconds']



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

plt.savefig('out/hist.png', dpi=300)
plt.close()


##########FIND THE LINE###########

