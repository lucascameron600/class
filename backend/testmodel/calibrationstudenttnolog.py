#compare the model's probability of arriving within THRESHOLD against what actually happened
#response ~ student_t(nu, alpha[station] + beta * osrm_meters, sigma), all in seconds. run from backend/

import numpy as np
import pandas as pd
from scipy.stats import t

#import VARIABLES

#posterior means from the stan fit

BETA = 0.081656
SIGMA = 0.198699
NU = 2.25001
#GAMMA = 37.033400
A = pd.read_csv('../stan/station_alpha.csv', index_col=0)['alpha']

THRESHOLD = 300         #seconds


def main():
    table = pd.read_parquet('../../data/workingfiles/cad/stan_table.parquet')

    night = (table['hour_of_day'] >= 22) | (table['hour_of_day'] < 6)
    mu = np.log(table['home_station'].map(A) + BETA * table['osrm_meters'])


    table['prob'] = t.cdf(np.log(THRESHOLD), df=NU, loc=mu, scale=SIGMA)


    table['made_it'] = table['total_response_seconds'] <= THRESHOLD

    print(f"within {THRESHOLD / 60:g} min. model: {table['prob'].mean():.1%}  actual: {table['made_it'].mean():.1%}")


    #when the model says 30%, does it happen about 30% of the time?
    bins = pd.cut(table['prob'], bins=np.linspace(0, 1, 11), include_lowest=True)
    calibration = table.groupby(bins, observed=True).agg(calls=('made_it', 'size'), predicted=('prob', 'mean'), actual=('made_it', 'mean'), )
    print("\ncalibration")
    print(calibration.round(3))

    print(f"brier: {((table['prob'] - table['made_it']) ** 2).mean():.4f}")


if __name__ == '__main__':
    main()
