import pandas as pd
import VARIABLES

df = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ, columns=["incident_id", "call_type", "unit_type", "is_code3"])

# incidents where an engine/truck responded, one row each (call_type is the same on every unit row)
inc = df[df["unit_type"].isin(['ENGINE'])]
#inc = df[df['is_code3'].eq(1)]

ct = inc["call_type"].str.lower()
bucket = pd.Series("other", index=inc.index)
bucket[ct.str.contains("fire")] = "fire"
bucket[ct.str.contains("alarm")] = "alarm"
bucket[ct.eq("medical incident")] = "medical"
bucket[ct.str.contains("traffic collision|extrication")] = "traffic"
print("What proportion of fire engine responses are medical in nature?")
print(pd.concat([bucket.value_counts(), bucket.value_counts(normalize=True).round(2)], axis=1))
