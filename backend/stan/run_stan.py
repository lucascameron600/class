from cmdstanpy import CmdStanModel


model = CmdStanModel(stan_file='regression.stan')

fit = model.sample(data='regression.json')

print(fit.summary())



