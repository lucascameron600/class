import json

import pandas as pd
from cmdstanpy import CmdStanModel


model = CmdStanModel(stan_file='regression.stan')

fit = model.sample(data='regression.json')

print(fit.summary().loc[['beta', 'sigma', 'nu']])

# each station's intercept in seconds, saved for the plotting script
with open('station_lookup.json') as f:
    station_ids = json.load(f)

alpha = pd.Series(fit.stan_variable('alpha').mean(axis=0), index=station_ids, name='alpha')
alpha.to_csv('station_alpha.csv')
