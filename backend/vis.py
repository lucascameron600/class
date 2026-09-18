import pandas as pd
import VARIABLES
from aquarel import load_theme
import seaborn as sea
import matplotlib.pyplot as plt
from filterdata1 import keep_dates
import numpy as np


def main():

    all_resp_2018_23 = pd.read_parquet(VARIABLES.POST_ET_CAD_PARQ)

    mask = (all_resp_2018_23['is_suppression'] & all_resp_2018_23['is_code3'])
    clean = all_resp_2018_23[mask]

    kde_sidebyside_vis_covid(clean, "all suppression unit", "SF Suppression Units")
    plot_multi_hist(clean, "Response Intervals Code 3 Suppression Unit -> Scene")



def plot_hist(series, title=""):
    s1 = np.log(series)
    fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,4))
    s1.plot(kind='hist', bins=200, ax=ax1)

    # Add labels and show the plot
    ax1.set_title(title)
    #ax1.set_xscale('symlog')
    ax1.set_xlabel('Seconds')
    ax1.set_ylabel('Frequency')


    series.plot(kind='hist', bins=200, ax=ax2)

    ax2.set_title(title)
    ax2.set_xlabel('Seconds')
    ax2.set_ylabel('Frequency')

    fig.savefig(f"{title}.png", dpi=700)
    plt.close(fig)


def plot_multi_hist(dataframe, title=""):

    cols = ["alarm_handling_seconds", "turnout_seconds", "travel_time_seconds", "total_response_seconds", "response_from_alarm_seconds", "commit_seconds"]

    theme = load_theme('umbra_dark')

    theme.apply()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    bins = np.arange(0, 3000 + 15, 15) #arbitrary 15min bin length, switch for data inspection
    for column, ax in zip(cols, axes.flat):
        dataframe[column].plot(kind='hist', bins=bins, ax=ax)
        ax.set_title(f"{column} n={dataframe[column].notna().sum(): }")
        ax.set_xlabel('Seconds')
        ax.set_ylabel('Frequency')

    fig.suptitle(title)
    plt.xlim(0,5000)
    fig.tight_layout()
    fig.savefig(f"{title}.png", dpi=700)
    plt.close(fig)
    theme.apply_transforms()


#The shape of probability distribution normalized so every kde has 1 under its curve
def kde_sidebyside_vis_covid(dataframe, describe='', title=''):
    theme = load_theme('umbra_dark')
    theme.apply()

    #mean_val = df1['travel_time_seconds'].mean()
    #median_val = df1['travel_time_seconds'].median()

    df1 = keep_dates(dataframe, start_date='2019-03-02', end_date='2020-02-01').copy()
    df2 = keep_dates(dataframe, start_date='2020-03-01', end_date='2021-02-01').copy()
    df3 = keep_dates(dataframe, start_date='2022-03-01', end_date='2023-02-01').copy()

    df1['year group'] = (f"Mar-Feb 2019-2020 (pre-shelter in place) {describe} responses to 911 calls n={len(df1)}")
    df2['year group'] = (f"Mar-Feb 2020-2021 (shelter in place) {describe} responses to 911 calls n={len(df2)}")
    df3['year group'] = (f"Mar-Feb 2022-2023 (post-shelter in place) {describe} responses to 911 calls n={len(df3)}")
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
    fig.savefig("covid_before_after_SFFD_transporting_units_travel_time_to_call.png", dpi = 700)
    plt.close(fig)
    theme.apply_transforms()


if __name__ == '__main__':
    main()
