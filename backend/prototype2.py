#probability a unit arrives within THRESHOLD at every call location, from the lognormal stan fit:
#log(response) ~ normal(log(alpha + beta * osrm_meters), sigma)
#uses each call's own osrm_meters from pre_stan.py, so no routing here. run from backend/

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from aquarel import load_theme
from pyproj import Transformer

import VARIABLES

#posterior means from the lognormal stan fit
ALPHA = 176.51          #seconds
BETA = 0.086213         #seconds per meter
SIGMA = 0.312787        #spread on the log scale, not seconds

THRESHOLD = 300         #seconds

def main():
    table = pd.read_parquet(VARIABLES.STAN_TABLE_PARQ)

    TO_ALBERS = Transformer.from_crs('EPSG:4326', 'EPSG:3310', always_xy=True)

    #the model's chance each call arrived in time, and whether it actually did
    table['prob'] = norm.cdf((np.log(THRESHOLD) - np.log(ALPHA + BETA * table['osrm_meters'])) / SIGMA)
    table['made_it'] = table['total_response_seconds'] <= THRESHOLD
    expected, actual = table['prob'].mean(), table['made_it'].mean()
    print(f"within {THRESHOLD / 60:g} min. model: {expected:.1%}  actual: {actual:.1%}")

    #one dot per call location, averaged over the calls there
    calls = table.groupby(['call_latitude', 'call_longitude'], as_index=False)['prob'].mean()
    stations = table[['station_latitude', 'station_longitude']].drop_duplicates()

    theme = load_theme('solarized_dark')
    theme.apply()

    calls = calls.sort_values('prob')      #high chances drawn last so dense areas show their typical value

    #project to california albers, meters -> km so the axes read cleanly
    cx, cy = TO_ALBERS.transform(calls['call_longitude'].to_numpy(), calls['call_latitude'].to_numpy())
    sx, sy = TO_ALBERS.transform(stations['station_longitude'].to_numpy(), stations['station_latitude'].to_numpy())
    cx, cy, sx, sy = cx / 1000, cy / 1000, sx / 1000, sy / 1000

    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    dots = ax.scatter(cx, cy, c=calls['prob'], cmap='YlGn', vmin=0, vmax=1, s=4, linewidths=0)
    ax.scatter(sx, sy, marker='^', s=70, c='#1a1a19', edgecolors='white', linewidths=1.2, label='station')
    ax.set_aspect('equal')                 #albers units are true distances, no cos(lat) fudge needed
    ax.set_xlabel('easting (km, California Albers)')
    ax.set_ylabel('northing (km)')
    ax.legend(loc='upper left')
    ax.set_title(f"Probability a unit arrives within {THRESHOLD / 60:g} minutes, at each call location\n"
                 f"model: {expected:.0%}   actual: {actual:.0%}")
    fig.colorbar(dots, ax=ax, label='probability (lognormal model)', shrink=0.8)
    fig.savefig('out/coverage_calls.png', dpi=500)
    theme.apply_transforms()               #before saving, so the theme's touches end up in the file

if __name__ == '__main__':
    main()
