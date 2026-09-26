import pandas as pd
import numpy as np
import seaborn as sea
import matplotlib.pyplot as plt
from aquarel import load_theme
from filterdata1 import keep_dates
import VARIABLES


def main():
    all_resp_23_26 = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)
    print(f'{len(all_resp_23_26):,} rows extracted from parq  ')

    engine_mask = (all_resp_23_26['is_code3'] & all_resp_23_26['unit_type'].isin(['ENGINE']))
    clean = all_resp_23_26[engine_mask]


    print(clean.describe().T)
    print(clean.head(9).T)
    print(clean.tail(9).T)


    #kde_sidebyside_vis_covid(clean, "all transport unit", "SF Transport Units")
    #plot_multi_hist(clean, "Response Intervals, transporting units, Code 3 only")
    #plot_hist(clean['total_response_seconds'], 'Total_response_seconds, transport only, code 3')
    #kde_by_station(clean, station_col='station_area', title='stations_suppression')
    boxplot_by_engine(clean, station_col='unit_id', title='Per engine travel time all calls')

    ambulance_mask = (all_resp_23_26['is_transport'] & all_resp_23_26['is_code3'])
    ambulances = all_resp_23_26[ambulance_mask]
    boxplot_by_neighborhood(ambulances, title='ambulance response time by neighborhood code 3')


#------------------------------------------------------
#-----------------PLOTTING_FUNCS-----------------------
#------------------------------------------------------
def plot_hist(series, title=""):
    s1 = np.log(series)
    fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,4))
    s1.plot(kind='hist', bins=200, ax=ax1)

    # Add labels and show the plot
    ax1.set_title(title)
    ax1.axvline(s1.median(), color='red')
    ax1.axvline(s1.mean(), color='tomato', linestyle='--')
    ax1.set_xlabel('Seconds(Log Transformed)')
    ax1.set_ylabel('Frequency')

   #_________________________________

    series.plot(kind='hist', bins=200, ax=ax2)

    ax2.set_title(title)
    ax2.axvline(series.median(), color='red')
    ax2.axvline(series.mean(), color='tomato', linestyle='--')
    ax2.set_xlabel('Seconds')
    ax2.set_ylabel('Frequency')

    fig.savefig(f"{title}.png", dpi=300)
    plt.close(fig)

##
def plot_multi_hist(dataframe, title=""):

    cols = ["alarm_handling_seconds", "turnout_seconds", "travel_time_seconds", "total_response_seconds", "response_from_alarm_seconds", "commit_seconds"]

    theme = load_theme('umbra_dark')
    theme.apply()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    bins = np.arange(0, 5000 + 15, 15) #arbitrary 15min bin length, switch for data inspection
    for column, ax in zip(cols, axes.flat):
        dataframe[column].plot(kind='hist', bins=bins, ax=ax)
        ax.set_title(f"{column} n={dataframe[column].notna().sum(): }")
        ax.set_xlim(0,3000)
        ax.set_xlabel('Seconds')
        ax.set_ylabel('Frequency')

    fig.suptitle(title)
    plt.xlim(0,5000)
    fig.tight_layout()
    fig.savefig(f"{title}.png", dpi=300)
    plt.close(fig)
    theme.apply_transforms()


#The shape of probability distribution normalized so every kde has 1 under its curve
def kde_sidebyside_vis_covid(dataframe, describe='', title=''):
    theme = load_theme('umbra_dark')
    theme.apply()

    #mean_val = df1['travel_time_seconds'].mean()
    #median_val = df1['travel_time_seconds'].median()

    df1 = keep_dates(dataframe, start_date='2019-03-01', end_date='2020-02-01').copy()
    df2 = keep_dates(dataframe, start_date='2020-03-01', end_date='2021-02-01').copy()
    df3 = keep_dates(dataframe, start_date='2022-03-01', end_date='2023-02-01').copy()

    df1['year group'] = (f"Mar-Feb 2019-2020 (pre-shelter in place) {describe} responses (n={len(df1)}) to 911 calls")
    df2['year group'] = (f"Mar-Feb 2020-2021 (shelter in place) {describe} responses (n={len(df2)}) to 911 calls")
    df3['year group'] = (f"Mar-Feb 2022-2023 (post-shelter in place) {describe} responses (n={len(df3)}) to 911 calls")
    combined_df = pd.concat([df1, df2, df3], ignore_index=True) #seaborn is weird so i need to reset indexes

    fig, ax = plt.subplots(figsize=(12, 7))

    #a single kde plot showing both density distributions over travel time in seconds
    #common_norm set to 0 so volume changes dont influence the "shape" of the distribution
    sea.kdeplot(data=combined_df, x='travel_time_seconds', hue='year group', common_norm=False, fill=True, alpha=0.20, cut=0, ax=ax)
    #ax.axvline(mean_val, color='red', linestyle='--')
    #ax.axvline(median_val, color='red')


    ax.set_xlim(0, 2000)
    ax.set_xlabel("Travel Time Seconds(clipped to 1-2000s to control outlier stamps)")
    ax.set_ylabel("Probability Density")
    ax.set_title(f'{title}, Lights and Sirens Travel Time To 911 Scene')
    fig.savefig("covid_before_after_SFFD_transporting_units_travel_time_to_call.png", dpi = 300)
    plt.close(fig)
    theme.apply_transforms()


def boxplot_by_engine(dataframe, station_col=None, title=''):

    theme = load_theme('umbra_dark')
    theme.apply()

    dataframe[station_col] = dataframe[station_col].astype(str)

    dataframe['engine'] = dataframe[station_col] + " (n=" + dataframe[station_col].map(dataframe[station_col].value_counts()).astype(str) + ")"
    order = dataframe.groupby('engine')['travel_time_seconds'].median().sort_values().index #fastest to slowest

    fig, ax = plt.subplots(figsize=(10, 14))

    #whiskers go from the 10th to the 90th percentile, outlier dots hidden
    sea.boxplot(data=dataframe, x='travel_time_seconds', y='engine', order=order, whis=(10, 90), showfliers=False, ax=ax)

    ax.axvline(dataframe['travel_time_seconds'].median(), color='red')
    ax.set_xlim(0, 750)
    ax.set_xlabel("Travel Time Seconds (whiskers 10th-90th percentile)")
    ax.set_ylabel("Engine")
    ax.set_title(title)
    theme.apply_transforms()
    fig.savefig(f"{title}.png", dpi=300)
    plt.close(fig)

def boxplot_by_neighborhood(dataframe, area_col='neighborhood', time_col='total_response_seconds', title=''):

    theme = load_theme('umbra_dark')
    theme.apply()

    df = dataframe.dropna(subset=[area_col, time_col]).copy()
    df[area_col] = df[area_col].astype(str)
    df['area'] = df[area_col] + " (n=" + df[area_col].map(df[area_col].value_counts()).astype(str) + ")"
    order = df.groupby('area')[time_col].median().sort_values().index #fastest to slowest

    fig, ax = plt.subplots(figsize=(10, 14))

    #whiskers go from the 10th to the 90th percentile, outlier dots hidden
    sea.boxplot(data=df, x=time_col, y='area', order=order, whis=(10, 90), showfliers=False, ax=ax)

    ax.axvline(df[time_col].median(), color='red')
    ax.set_xlabel(f"{time_col} (whiskers 10th-90th percentile)")
    ax.set_ylabel("")
    ax.set_title(title)
    theme.apply_transforms()
    fig.savefig(f"{title}.png", dpi=300)
    plt.close(fig)

if __name__ == '__main__':
    main()
