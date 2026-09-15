import pandas as pd
pd.read_csv("Fire_Department_and_Emergency_Medical_Services_Dispatched_Calls_for_Service_20260908.csv", dtype=str).to_parquet("raw_cad_sf.parquet")
