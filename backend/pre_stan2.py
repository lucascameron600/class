import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from filterdata1 import data_printout
import cmdstanpy


import VARIABLES



def main():

    table = pd.read_parquet(VARIABLES.STAN_TABLE_PARQ)

    data_printout(table)

    stan = {
            "N": len(table['osrm_seconds']),
            "x": table['osrm_meters'],
            "y": table['total_response_seconds'],
            }

    cmdstanpy.write_stan_json('stan/regression.json', stan)

if __name__ == '__main__':
    main()


