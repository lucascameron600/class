import json

import pandas as pd
from cmdstanpy import CmdStanModel


model = CmdStanModel(stan_file='regression.stan')

fit = model.sample(data='regression.json')

print(fit.summary().loc[['beta', 'sigma', 'nu', 'p_night']])



# each stations intercept or alpha in seconds
with open('station_lookup.json') as f:
    saved = json.load(f)

station_ids = []
for stan_index in range(1, len(saved) + 1):

    station_ids.append(saved[str(stan_index)])


alpha = pd.Series(fit.stan_variable('alpha').mean(axis=0), index=station_ids, name='alpha')
alpha.to_csv('station_alpha.csv')
