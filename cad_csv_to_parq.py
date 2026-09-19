import pandas as pd
pd.read_csv("raw_sf_cad_short.csv", dtype=str).to_parquet("raw_sf_cad.parquet")
#use head -n xxxnumlines raw_sf_cad.csv > clipped_sf_cad.csv
