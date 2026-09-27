import pandas as pd
import VARIABLES

df = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ, columns=["incident_id", "call_type", "unit_type"])

#incidents where an engine responded any response code3 and 2 included
inc = df[df["unit_type"].isin(['ENGINE'])]

ct = inc["call_type"].str.lower()
bucket = pd.Series("medical/TC/OTHER", index=inc.index)


bucket[ct.str.contains("fire")] = "fire"
bucket[ct.str.contains("alarm")] = "alarm"

bucket[ct.isin(["medical incident",'traffic collission', 'extrication'])] = "medical/TC/OTHER"

print("What proportion of fire engine responses are medical/TC in nature?")
print(pd.concat([bucket.value_counts(), bucket.value_counts(normalize=True).round(2)], axis=1))
