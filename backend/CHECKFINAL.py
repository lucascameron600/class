import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from good_trips import flag_all_osrm_route
import VARIABLES
from sklearn.model_selection import GroupKFold
from scipy.spatial import cKDTree
import os
from scipy.stats import norm
from scipy.optimize import minimize

trips = pd.read_parquet(VARIABLES.GOOD_TRIPS_PARQ)


#####ROUTED
trips = flag_all_osrm_route(trips,['station_latitude', 'station_longitude'],
                                ['call_latitude', 'call_longitude'], 'route')




#######SNAP
SHARE_WITHIN_METERS = 25                   # next to TARGET_SECONDS

# right after trips = flag_all_osrm_route(...)
keys = ["home_station", "call_latitude", "call_longitude"]
pairs = trips.dropna(subset=["route_meters"]).drop_duplicates(keys)[keys + ["route_meters"]].copy()

## the call points in meters, so that distances between them are meters
pairs["x"] = np.radians(pairs["call_longitude"]) * 6371000 * np.cos(np.radians(pairs["call_latitude"].mean()))
pairs["y"] = np.radians(pairs["call_latitude"]) * 6371000

for station, group in pairs.groupby("home_station"):
    xy = group[["x", "y"]].to_numpy()
    nearby = cKDTree(xy).query_ball_point(xy, r=SHARE_WITHIN_METERS)      # for each point: the points in reach, itself included
    route = group["route_meters"].to_numpy()
    pairs.loc[group.index, "shared_route_meters"] = [route[i].min() for i in nearby]

print(f"{(pairs['shared_route_meters'] < pairs['route_meters']).sum():,} of {len(pairs):,} station + call point pairs got a shorter route")
trips = trips.merge(pairs[keys + ["shared_route_meters"]], on=keys, how="left")
trips["route_meters"] = trips["shared_route_meters"]




trips = trips[trips['gcd_meters'].notna()]

###########


##NOT SET YET
trips = trips[trips['idle_seconds'] > 300]




trips['kmph'] = (trips['gcd_meters'] / trips['travel_time_seconds']) * 3.6

###############################
def p90_by_distance(trips):
    ## 90th percentile of the outcome for calls about 0.5, 1 and 2 km away in a straight line
    bands = [(400, 600), (900, 1100), (1900, 2100)]
    return [trips.loc[trips['gcd_meters'].between(low, high), 'total_response_seconds'].quantile(0.9) for low, high in bands]

def show(label, kept):
    near, mid, far = p90_by_distance(kept)
    overall = kept['total_response_seconds'].quantile(0.9)

    print(f'{label:<22} {len(kept):>8,}   {overall:>6.0f} {near:>6.0f} {mid:>6.0f} {far:>6.0f}')

print('\nfilter                 trips kept   p90 at 0.5, 1, 2 km (s)')
show('no speed filter', trips)
for slow in [0, 1, 2, 3, 5, 7, 10]:
    show(f'drop under {slow} km/h', trips[trips['kmph'] >= slow])

for fast in [90, 70, 50, 40]:
    show(f'drop over {fast} km/h', trips[trips['kmph'] <= fast])
###################################3

##DROP UNDER OR OVER
trips['over_50'] = trips['kmph'] > 90
trips['under_5'] = trips['kmph'] < 1

## CHANGED: count before dropping. the old print ran after the drop so it always showed 0
print(f"dropping {trips['over_50'].sum():,} trips over 90 km/h and {trips['under_5'].sum():,} under 1 km/h")

trips = trips[~trips['over_50']]
trips = trips[~trips['under_5']]


meters = trips[['gcd_meters']]
seconds = trips['total_response_seconds']


##CHECK DISTRIBUTION OF KMPH PER HOUR
#plt.hist(trips['kmph'], bins = 8000)
#plt.axvline(trips['kmph'].median(), color='red')
#plt.axvline(trips['kmph'].mean(), color='tomato',linestyle='--')
#plt.xlim(0,300)


## SIMPLIFIED RAND USING GCD
## paper says erorr increases with distance!

model = LinearRegression().fit(meters,seconds)
log_error = np.log(seconds) - np.log(model.predict(meters))


print(f'\nlog rmse = {log_error.std()}')
print(f'y intercept = {model.intercept_} s')

print('\nKOLESAR/RAND simplified formula via NFPA T = 45 + 1.7D')

print(f'R^2 = {model.score(meters,seconds)}')
print(f'MODEL_SLOPE = {model.coef_}')

plt.scatter(meters,seconds,color='blue',s=.01)

plt.xlabel("gcd_meters")
plt.ylabel("total response seconds")

print(f'wrote out/hist.png')
plt.savefig('out/hist.png', dpi=600)
plt.close()


###### DELTEE

keys = ['home_station', 'call_latitude', 'call_longitude']
trips['log_t'] = np.log(trips['total_response_seconds'])
common = trips[trips.groupby(keys)['log_t'].transform('size') >= 30]
within = common['log_t'] - common.groupby(keys)['log_t'].transform('mean')
print('floor for log error:', within.std())


## FREQUENT LOCATION
pts = trips.groupby(['home_station', 'Address']).agg(
    n=('total_response_seconds', 'size'),
    median_total=('total_response_seconds', 'median'),
    over_270=('total_response_seconds', lambda s: (s > 320).mean()),
    route=('route_meters', 'first'))
print(pts[pts['n'] >= 20].sort_values('median_total', ascending=False).head(25))

trips['excess'] = trips['total_response_seconds'] - (195 + 0.087 * trips['route_meters'])
pts = trips.groupby(['home_station', 'Address']).agg(
    n=('excess', 'size'), excess=('excess', 'median'), route=('route_meters', 'first'))
print(pts[pts['n'] >= 20].sort_values('excess', ascending=False).head(25))





d = trips.dropna(subset=['gcd_meters', 'route_meters', 'route_duration']).copy()
d['log_t'] = np.log(d['total_response_seconds'])
keys = ['home_station', 'call_latitude', 'call_longitude']

def score(col):
    pred = np.empty(len(d))
    for tr, te in GroupKFold(n_splits=5).split(d, groups=d['home_station']):
        m = LinearRegression().fit(d[[col]].iloc[tr], d['total_response_seconds'].iloc[tr])
        pred[te] = m.predict(d[[col]].iloc[te])
    d['res'] = d['log_t'] - np.log(pred)
    g = d.groupby(keys)['res']
    pair = g.mean()[g.size() >= 20]
    return d['res'].std(), np.sqrt((pair ** 2).mean())

for col in ['gcd_meters', 'route_meters', 'route_duration']:
    trip_err, pair_err = score(col)
    print(f'{col:<16} trip {trip_err:.3f}   pair {pair_err:.3f}')

score('route_meters')                      # leaves d['res'] from this model
g = d.groupby(keys)['res']
pair = g.mean()[g.size() >= 20].reset_index()
st = pair.groupby('home_station')['res'].transform('mean')

print('station part       ', np.sqrt((st ** 2).mean()))
print('within-station part', np.sqrt(((pair['res'] - st) ** 2).mean()))


## CHANGED: new helper, used by both probability blocks below
def empirical_prob(train_resid, gap):
    ## share of real log errors small enough to still make the target
    ## replaces norm.cdf, which assumed the errors follow a bell curve
    sorted_resid = np.sort(np.asarray(train_resid))
    return np.searchsorted(sorted_resid, np.asarray(gap), side='right') / len(sorted_resid)


TARGET_SECONDS = 320

## CHANGED: routed meters instead of OSRM duration.
## it beat OSRM duration and straight-line distance in the comparison at the bottom
X_COL = "route_meters"
Y_COL = "total_response_seconds"

needed = [
    X_COL,
    Y_COL,
    "call_latitude",
    "call_longitude",
]

d = trips.dropna(subset=needed).copy()

# Keep valid positive values only.
d = d[
    (d[X_COL] > 0)
    & (d[Y_COL] > 0)
    & d["call_latitude"].between(-90, 90)
    & d["call_longitude"].between(-180, 180)
].copy()

# Optional: remove extreme total response outliers for this quick visual test.
# Adjust or delete these if you want.
d = d[d[Y_COL].between(1, VARIABLES.MAX_TRAVEL_SECONDS)].copy()

# -----------------------------
# Fit the trip model from Westgate et al. 2016 (the Toronto ambulance paper)
# -----------------------------
## CHANGED: the middle and the spread of the response time come from their model (equation 1 in the paper),
## not from the log-log line. on the log scale
##     center   = time bin effect + log(c + u * route_meters)
##     variance = M * exp(-lam * route_meters) + delta       short trips vary more on the log scale
## what is not the same as the paper:
##   - one road class. they fit a speed for each of seven road classes along the path.
##     all this script knows about a path is its total routed meters, so there is a single u
##   - seconds here run from dispatch to on scene, theirs start when the wheels roll, so c also holds the turnout
##   - fitted by maximum likelihood, which takes seconds. they run MCMC for 18 hours, which also gives
##     intervals on the parameters. with this many trips the estimates themselves should come out close
##   - the paper reads the probability off a bell curve around that center.
##     here it is read off the real errors, see just below the fit

## the paper's four time bins
hour = d["hour_of_day"]
weekend = d["day_of_week"] >= 5                    # monday is 0
d["time_bin"] = 0                                  # weekday off peak, the baseline
d.loc[~weekend & (hour.between(6, 9) | hour.between(15, 18)), "time_bin"] = 1      # weekday rush hour
d.loc[weekend & hour.between(6, 21), "time_bin"] = 2                               # weekend daytime
d.loc[(hour >= 22) | (hour < 6), "time_bin"] = 3                                   # late night

route_m = d[X_COL].to_numpy()
y = np.log(d[Y_COL].to_numpy())
time_bin = d["time_bin"].to_numpy()


def unpack(theta):
    ## c, u, M, delta and lam are searched on the log scale so they can never go negative
    c, u = np.exp(theta[0]), np.exp(theta[1])
    mu = np.array([0.0, theta[2], theta[3], theta[4]])        # the baseline bin is fixed at 0
    M, delta, lam = np.exp(theta[5]), np.exp(theta[6]), np.exp(theta[7])
    return c, u, mu, M, delta, lam


def negative_log_likelihood(theta):
    c, u, mu, M, delta, lam = unpack(theta)
    variance = M * np.exp(-lam * route_m) + delta
    error = y - mu[time_bin] - np.log(c + u * route_m)
    return 0.5 * np.mean(np.log(variance) + error ** 2 / variance)


## the search starts from a straight line through the trips
slope, intercept = np.polyfit(route_m, d[Y_COL], 1)
c_start, u_start = np.clip(intercept, 5, 500), np.clip(slope, 0.01, 0.5)
variance_start = np.var(y - np.log(c_start + u_start * route_m))
start = [np.log(c_start), np.log(u_start), 0, 0, 0, np.log(variance_start), np.log(variance_start), np.log(1 / 1000)]
limits = [(np.log(1), np.log(1000)), (np.log(0.001), np.log(1)), (-1, 1), (-1, 1), (-1, 1),
          (np.log(1e-6), np.log(10)), (np.log(1e-4), np.log(10)), (np.log(1e-6), np.log(0.1))]

fit = minimize(negative_log_likelihood, start, method="L-BFGS-B", bounds=limits, jac="3-point")
c, u, mu, M, delta, lam = unpack(fit.x)


def westgate(route_meters, time_effect):
    ## where the log of the response time is centered for a trip of this routed length, and its sd
    log_center = time_effect + np.log(c + u * route_meters)
    log_sd = np.sqrt(M * np.exp(-lam * route_meters) + delta)
    return log_center, log_sd


d["pred_log_total"], log_sd = westgate(route_m, mu[time_bin])
d["residual"] = y - d["pred_log_total"]

## CHANGED: the paper assumes the errors follow a bell curve. on these trips they do not. they are bunched
## closer to the middle than a bell curve, with a few very long trips, and the bell curve put the on-time
## share too low. so the shape now comes from the trips themselves: every error divided by its sd.
## the center and the sd are still the paper's
scaled_error = (d["residual"] / log_sd).to_numpy()
error_q10, error_q50, error_q90 = np.quantile(scaled_error, [0.10, 0.50, 0.90])

# Predicted median and 90th percentile on original seconds scale.
d["pred_median_total"] = np.exp(d["pred_log_total"] + error_q50 * log_sd)
d["pred_p90_total"] = np.exp(d["pred_log_total"] + error_q90 * log_sd)

# Probability of meeting target.
## the share of real scaled errors small enough to still make the target
d["p_on_time"] = empirical_prob(scaled_error, (np.log(TARGET_SECONDS) - d["pred_log_total"]) / log_sd)

# Actual outcome for quick validation.
d["actual_on_time"] = d[Y_COL] <= TARGET_SECONDS

## the next two are kept only so the printout can show all three on the same trips:
## the paper's model exactly as published, with its bell curve
bell_p = norm.cdf((np.log(TARGET_SECONDS) - d["pred_log_total"]) / log_sd)

## and the earlier log-log model with its real error spread
earlier = LinearRegression().fit(np.log(d[[X_COL]]), y)
earlier_log = earlier.predict(np.log(d[[X_COL]]))
earlier_p = empirical_prob(y - earlier_log, np.log(TARGET_SECONDS) - earlier_log)


def brier_and_gap(p, on_time):
    ## brier score, and the average distance between predicted and actual on-time share over ten probability buckets
    scored = pd.DataFrame({"p": np.asarray(p, dtype=float), "on_time": np.asarray(on_time, dtype=float)})
    scored["bucket"] = np.minimum((scored["p"] * 10).astype(int), 9)
    buckets = scored.groupby("bucket").agg(n=("p", "size"), p=("p", "mean"), actual=("on_time", "mean"))
    gap = ((buckets["p"] - buckets["actual"]).abs() * buckets["n"]).sum() / buckets["n"].sum()
    return ((scored["p"] - scored["on_time"]) ** 2).mean(), gap


this_brier, this_gap = brier_and_gap(d["p_on_time"], d["actual_on_time"])
bell_brier, bell_gap = brier_and_gap(bell_p, d["actual_on_time"])
earlier_brier, earlier_gap = brier_and_gap(earlier_p, d["actual_on_time"])

print("\n================ WESTGATE TRIP MODEL ================")
print(f"target seconds:              {TARGET_SECONDS}")
print(f"x column:                    {X_COL}")
print(f"y column:                    {Y_COL}")
print(f"rows used:                   {len(d):,}")
print(f"search converged:            {fit.success}")
if not fit.success:
    print(f"search stopped because:      {fit.message}")
print(f"c, seconds at zero meters:   {c:.1f}")
print(f"u, seconds per meter:        {u:.4f}   ({3.6 / u:.0f} km/h)")
print(f"mu rush hour:                {mu[1]:+.4f}")
print(f"mu weekend daytime:          {mu[2]:+.4f}")
print(f"mu late night:               {mu[3]:+.4f}")
print(f"M, delta, lam:               {M:.4f}, {delta:.4f}, {lam:.5f}")
print(f"log sd at 300 m and 3000 m:  {westgate(300, 0)[1]:.3f}, {westgate(3000, 0)[1]:.3f}")
print(f"scaled error 10, 50, 90 pct: {error_q10:.3f}, {error_q50:.3f}, {error_q90:.3f}   (a bell curve gives -1.282, 0, 1.282)")
print(f"actual on-time share:        {d['actual_on_time'].mean():.3f}")
print(f"predicted on-time share:     {d['p_on_time'].mean():.3f}")
print(f"actual p90 total:            {d[Y_COL].quantile(0.9):.0f} seconds")
print(f"predicted p90 total median:  {d['pred_p90_total'].median():.0f} seconds")
print()
print("on the same trips, lower is better          brier score   calibration gap")
print(f"this model, real error shape (the one used)      {this_brier:.4f}            {this_gap:.4f}")
print(f"this model, bell curve as in the paper           {bell_brier:.4f}            {bell_gap:.4f}")
print(f"earlier log-log model, real error spread         {earlier_brier:.4f}            {earlier_gap:.4f}")
print("=====================================================\n")

# -----------------------------
# Calibration table
# -----------------------------
d["prob_bucket"] = pd.cut(
    d["p_on_time"],
    bins=np.arange(0, 1.01, 0.1),
    include_lowest=True,
)

calibration = d.groupby("prob_bucket", observed=True).agg(
    n=("actual_on_time", "size"),
    predicted_prob=("p_on_time", "mean"),
    actual_on_time_rate=("actual_on_time", "mean"),
    median_actual_seconds=(Y_COL, "median"),
    median_pred_seconds=("pred_median_total", "median"),
)

print("Calibration table:")
print(calibration)
print()

# -----------------------------
# Probability map
# -----------------------------
def probability_color(p):
    if p >= 0.90:
        return "darkgreen"
    elif p >= 0.75:
        return "green"
    elif p >= 0.60:
        return "lightgreen"
    elif p >= 0.45:
        return "orange"
    elif p >= 0.30:
        return "red"
    else:
        return "darkred"


center_lat = d["call_latitude"].median()
center_lon = d["call_longitude"].median()

## CHANGED: one dot per call location, whichever engines went there.
## it used to be one dot per station + location, so when two engines had been to the same
## address their dots sat exactly on top of each other and only the top one could be clicked
d["point_id"] = d.groupby(["call_latitude", "call_longitude"]).ngroup()

map_points = d.groupby("point_id").agg(
    lat=("call_latitude", "first"),
    lon=("call_longitude", "first"),
    address=("Address", "first"),
    n=("actual_on_time", "size"),
    actual_share=("actual_on_time", "mean"),
    p_on_time=("p_on_time", "mean"),
    median_actual=(Y_COL, "median"),
).reset_index()
map_points["address"] = map_points["address"].fillna("no address")

## CHANGED: this cap is only about the size of the html file now.
## Raise it to see the quiet locations too. The busiest call points are the ones kept.
MAX_POINTS = 8000

if len(map_points) > MAX_POINTS:
    map_points = map_points.nlargest(MAX_POINTS, "n")

## CHANGED: which engines went to each location and how many calls each. the popup lists these
map_engines = d.groupby(["point_id", "unit_id"]).agg(
    n=("actual_on_time", "size"),
    actual_share=("actual_on_time", "mean"),
    p_on_time=("p_on_time", "mean"),
    route_meters=("route_meters", "first"),
).reset_index()
map_engines = map_engines[map_engines["point_id"].isin(map_points["point_id"])]
map_engines = map_engines.sort_values("n", ascending=False)      # busiest engine first in the popup

## CHANGED: a dot's color is the chance of making it from the closest station, the way the paper draws
## its coverage map. it used to be an average over whichever engines happened to go there, so two
## neighboring dots with a different mix of engines got different colors.
## closest = the shortest routed distance among the stations that went to that location in these trips
closest = map_engines.sort_values("route_meters").drop_duplicates("point_id")
closest = closest.rename(columns={"unit_id": "closest_unit", "route_meters": "closest_route_m"})
map_points = map_points.merge(closest[["point_id", "closest_unit", "closest_route_m"]], on="point_id")

## for an average hour of the week, so the color depends on the distance and nothing else
closest_log_center, closest_log_sd = westgate(map_points["closest_route_m"], mu[time_bin].mean())
map_points["p_closest"] = empirical_prob(scaled_error, (np.log(TARGET_SECONDS) - closest_log_center) / closest_log_sd)
map_points["median_closest"] = np.exp(closest_log_center + error_q50 * closest_log_sd)
map_points["p90_closest"] = np.exp(closest_log_center + error_q90 * closest_log_sd)

map_points["color"] = map_points["p_closest"].apply(probability_color)
map_points["radius"] = 2.5 + 1.5 * np.log10(map_points["n"])      # bigger dot = more calls

## stations as black dots, so the green clumps can be read against them
stations = d[["home_station", "station_latitude", "station_longitude"]].drop_duplicates("home_station")

## CHANGED: the page is written out by hand, folium is not used any more.
## MapLibre draws the streets and the dots together on the graphics card, so nothing is redrawn
## dot by dot when the map moves, and a popup is only built for the dot that gets clicked.
## keep the @5.24.0 in the two unpkg links. the old page asked for the newest MapLibre, and
## version 6 stopped shipping maplibre-gl.js, so that link turned into a 404
MAP_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>P(total response within __TARGET__ s)</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
<style>
    html, body, #map { height: 100%; margin: 0; }
    body { font: 13px sans-serif; }
    #legend {
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 230px;
        z-index: 10;
        background-color: white;
        border: 2px solid gray;
        padding: 10px;
    }
    .dot-popup { font: 13px/1.4 sans-serif; }
    .dot-popup .address { display: block; margin-right: 14px; }
    .dot-popup .engine-list { max-height: 170px; overflow-y: auto; margin: 6px 0; }
    .dot-popup .group { margin-top: 6px; }
    .dot-popup table { border-collapse: collapse; }
    .dot-popup th, .dot-popup td { text-align: right; padding: 0 0 0 12px; }
    .dot-popup th:first-child, .dot-popup td:first-child { text-align: left; padding-left: 0; }
</style>
</head>
<body>
<div id="map"></div>
<div id="legend">
<b>Predicted P(total ≤ __TARGET__s)</b><br>
<span style="color: darkgreen;">●</span> ≥ 0.90<br>
<span style="color: green;">●</span> 0.75–0.90<br>
<span style="color: lightgreen;">●</span> 0.60–0.75<br>
<span style="color: orange;">●</span> 0.45–0.60<br>
<span style="color: red;">●</span> 0.30–0.45<br>
<span style="color: darkred;">●</span> &lt; 0.30<br>
<br>
One dot per call location<br>
Color is from the closest station<br>
Bigger dot = more calls<br>
Click a dot for its engines and calls<br>
Black dots are stations<br>
Model is in-sample quick test
</div>
<script>
const POINTS = __POINTS__;        // one row per dot
const ENGINES = __ENGINES__;      // one row per engine at a dot
const STATIONS = __STATIONS__;

// the engine rows of each dot, ready for when its popup is opened
const enginesAt = {};
for (const row of ENGINES) {
    if (!enginesAt[row.point_id]) { enginesAt[row.point_id] = []; }
    enginesAt[row.point_id].push(row);
}

// addresses are data, not html
function esc(text) {
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function popupHtml(pt) {
    const engines = enginesAt[pt.point_id] || [];
    let rows = '';
    for (const e of engines) {
        rows += '<tr><td>' + esc(e.unit_id) + '</td><td>' + e.n + '</td><td>' + Math.round(e.route_meters) +
            '</td><td>' + e.p_on_time.toFixed(2) + '</td><td>' + e.actual_share.toFixed(2) + '</td></tr>';
    }
    return '<div class="dot-popup">' +
        '<b class="address">' + esc(pt.address) + '</b>' +
        '<b>Calls here:</b> ' + pt.n + ' from ' + engines.length + (engines.length === 1 ? ' engine' : ' engines') +
        '<div class="engine-list"><table>' +
        '<tr><th>Engine</th><th>Calls</th><th>Route m</th><th>Pred P</th><th>Actual</th></tr>' + rows +
        '</table></div>' +
        // the dot is colored by the first group
        '<b>From the closest station</b> (' + esc(pt.closest_unit) + ', ' + Math.round(pt.closest_route_m) + ' m, average hour)<br>' +
        'Predicted P(on time): ' + pt.p_closest.toFixed(2) + '<br>' +
        'Pred median: ' + Math.round(pt.median_closest) + ' sec<br>' +
        'Pred p90: ' + Math.round(pt.p90_closest) + ' sec' +
        '<div class="group"><b>All calls here</b></div>' +
        'Actual on-time share: ' + pt.actual_share.toFixed(2) + ' (model for the same trips: ' + pt.p_on_time.toFixed(2) + ')<br>' +
        'Median actual: ' + Math.round(pt.median_actual) + ' sec' +
        '</div>';
}

function drawMap() {
    const map = new maplibregl.Map({
        container: 'map',
        style: 'https://tiles.openfreemap.org/styles/positron',
        center: __CENTER__,
        zoom: 11,               // the same view as zoom 12 in Leaflet, MapLibre counts one lower
        dragRotate: false       // north stays up
    });
    map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-left');

    map.on('load', function () {
        map.addSource('calls', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: POINTS.map(function (pt, i) {
                    return {
                        type: 'Feature',
                        geometry: {type: 'Point', coordinates: [pt.lon, pt.lat]},
                        properties: {i: i, n: pt.n, color: pt.color, radius: pt.radius}
                    };
                })
            }
        });
        map.addLayer({
            id: 'calls',
            type: 'circle',
            source: 'calls',
            layout: {'circle-sort-key': ['get', 'n']},      // busy dots end up on top
            paint: {
                'circle-radius': ['get', 'radius'],
                'circle-color': ['get', 'color'],
                'circle-opacity': 0.65
            }
        });

        map.addSource('stations', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: STATIONS.map(function (s) {
                    return {
                        type: 'Feature',
                        geometry: {type: 'Point', coordinates: [s.station_longitude, s.station_latitude]},
                        properties: {home_station: s.home_station}
                    };
                })
            }
        });
        map.addLayer({
            id: 'stations',
            type: 'circle',
            source: 'stations',
            paint: {'circle-radius': 6, 'circle-color': 'black'}
        });

        // the popup is built here, on the click, for this one dot
        map.on('click', 'calls', function (e) {
            const pt = POINTS[e.features[0].properties.i];
            new maplibregl.Popup({maxWidth: '360px'})
                .setLngLat([pt.lon, pt.lat])
                .setHTML(popupHtml(pt))
                .addTo(map);
        });
        map.on('mouseenter', 'calls', function () { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'calls', function () { map.getCanvas().style.cursor = ''; });

        const stationName = new maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 10});
        map.on('mouseenter', 'stations', function (e) {
            const station = e.features[0];
            stationName
                .setLngLat(station.geometry.coordinates)
                .setText('Station ' + station.properties.home_station)
                .addTo(map);
        });
        map.on('mouseleave', 'stations', function () { stationName.remove(); });
    });
}

if (typeof maplibregl === 'undefined') {
    document.getElementById('map').textContent =
        'The map library did not load from unpkg.com. Check the internet connection and reload.';
} else {
    try {
        drawMap();
    } catch (error) {
        document.getElementById('map').textContent = 'The map could not start: ' + error.message;
    }
}
</script>
</body>
</html>
"""

page = MAP_PAGE.replace("__TARGET__", str(TARGET_SECONDS))
page = page.replace("__CENTER__", f"[{float(center_lon)}, {float(center_lat)}]")
page = page.replace("__STATIONS__", stations.to_json(orient="records"))
page = page.replace("__ENGINES__", map_engines.to_json(orient="records", double_precision=6))
page = page.replace("__POINTS__", map_points.to_json(orient="records", double_precision=6))

out_path = "out/probability_coverage_calls.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(page)

print(f"wrote {out_path}")
print("Open that HTML file in your browser.")

print(f"median predicted p90: {d['pred_p90_total'].median():.0f}")
print(f"90th percentile of predicted medians: {d['pred_median_total'].quantile(0.9):.0f}")
print(f"mean predicted on-time: {d['p_on_time'].mean():.3f}")
print(f"actual on-time: {d['actual_on_time'].mean():.3f}")

print(f"median predicted p90: {d['pred_p90_total'].median():.0f}")
print(f"90th percentile of predicted medians: {d['pred_median_total'].quantile(0.9):.0f}")
print(f"mean predicted on-time: {d['p_on_time'].mean():.3f}")
print(f"actual on-time: {d['actual_on_time'].mean():.3f}")



p90_coverage = (d[Y_COL] <= d["pred_p90_total"]).mean()
print(f"actual share below predicted p90: {p90_coverage:.3f}")

## CHANGED: new check. 0.90 overall can hide 0.95 at short trips and 0.85 at long ones
band = pd.cut(d['route_meters'], [0, 500, 1000, 1500, 2500, 6000])
print("actual share below predicted p90, by routed distance:")
print((d[Y_COL] <= d["pred_p90_total"]).groupby(band, observed=True).mean())




import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold, KFold
from sklearn.metrics import mean_squared_error, median_absolute_error, brier_score_loss
from scipy.stats import norm

TARGET_SECONDS = 270
Y_COL = "total_response_seconds"

candidate_cols = [
    "gcd_meters",       # straight-line
    "route_meters",    # routed distance
    "route_duration",  # routed OSRM time
]

# Keep only columns that actually exist.
candidate_cols = [c for c in candidate_cols if c in trips.columns]

needed = candidate_cols + [Y_COL]

if "home_station" in trips.columns:
    needed.append("home_station")

d = trips.dropna(subset=needed).copy()

# Keep valid positive values.
d = d[d[Y_COL] > 0].copy()

for col in candidate_cols:
    d = d[d[col] > 0].copy()

# Optional: keep same total response filter you are already using.
d = d[d[Y_COL].between(1, VARIABLES.MAX_TRAVEL_SECONDS)].copy()

print("\n================ PREDICTOR COMPARISON ================")
print(f"rows used:      {len(d):,}")
print(f"target:         {Y_COL}")
print(f"time target:    {TARGET_SECONDS} seconds")
print(f"predictors:     {candidate_cols}")
print("======================================================\n")


def make_folds(df, n_splits=5):
    if "home_station" in df.columns and df["home_station"].nunique() >= n_splits:
        splitter = GroupKFold(n_splits=n_splits)
        return splitter.split(df, groups=df["home_station"])
    else:
        splitter = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        return splitter.split(df)


def score_predictor(df, x_col, y_col, target_seconds, n_splits=5):
    rows = []

    # Storage for all held-out predictions.
    all_test = []

    for fold_id, (train_idx, test_idx) in enumerate(make_folds(df, n_splits=n_splits), start=1):
        train = df.iloc[train_idx].copy()
        test = df.iloc[test_idx].copy()

        X_train = np.log(train[[x_col]])
        y_train_log = np.log(train[y_col])

        X_test = np.log(test[[x_col]])
        y_test = test[y_col].to_numpy()
        y_test_log = np.log(y_test)

        model = LinearRegression().fit(X_train, y_train_log)

        train_mu = model.predict(X_train)

        ## CHANGED: keep the training errors themselves instead of only their sigma
        resid = (y_train_log - train_mu).to_numpy()

        test_mu = model.predict(X_test)

        # Predicted median and p90 on original seconds scale.
        pred_median = np.exp(test_mu)

        ## CHANGED: real 90th percentile of the training errors instead of 1.28 * sigma
        pred_p90 = np.exp(test_mu + np.quantile(resid, 0.90))

        # Probability of meeting target.
        ## CHANGED: share of training errors that would have made the target, instead of norm.cdf
        p_on_time = empirical_prob(resid, np.log(target_seconds) - test_mu)

        actual_on_time = y_test <= target_seconds

        fold_result = pd.DataFrame({
            "fold": fold_id,
            "x_col": x_col,
            "actual_seconds": y_test,
            "actual_log": y_test_log,
            "pred_log": test_mu,
            "pred_median": pred_median,
            "pred_p90": pred_p90,
            "p_on_time": p_on_time,
            "actual_on_time": actual_on_time.astype(int),
        })

        all_test.append(fold_result)

    out = pd.concat(all_test, ignore_index=True)

    log_rmse = np.sqrt(mean_squared_error(out["actual_log"], out["pred_log"]))
    median_abs_error_s = median_absolute_error(out["actual_seconds"], out["pred_median"])
    brier = brier_score_loss(out["actual_on_time"], out["p_on_time"])

    actual_on_time_rate = out["actual_on_time"].mean()
    predicted_on_time_rate = out["p_on_time"].mean()

    p90_coverage = (out["actual_seconds"] <= out["pred_p90"]).mean()

    actual_p90_s = out["actual_seconds"].quantile(0.9)
    median_pred_p90_s = out["pred_p90"].median()

    # Calibration by probability bucket.
    out["prob_bucket"] = pd.cut(
        out["p_on_time"],
        bins=np.arange(0, 1.01, 0.1),
        include_lowest=True,
    )

    cal = out.groupby("prob_bucket", observed=True).agg(
        n=("actual_on_time", "size"),
        predicted_prob=("p_on_time", "mean"),
        actual_on_time_rate=("actual_on_time", "mean"),
    )

    cal["abs_calibration_error"] = (
        cal["actual_on_time_rate"] - cal["predicted_prob"]
    ).abs()

    weighted_calibration_error = (
        cal["abs_calibration_error"] * cal["n"]
    ).sum() / cal["n"].sum()

    summary = {
        "predictor": x_col,
        "log_rmse": log_rmse,
        "median_abs_error_s": median_abs_error_s,
        "brier": brier,
        "actual_on_time": actual_on_time_rate,
        "predicted_on_time": predicted_on_time_rate,
        "on_time_error": predicted_on_time_rate - actual_on_time_rate,
        "p90_coverage": p90_coverage,
        "p90_error_from_0.90": p90_coverage - 0.90,
        "actual_p90_s": actual_p90_s,
        "median_pred_p90_s": median_pred_p90_s,
        "weighted_calibration_error": weighted_calibration_error,
    }

    return summary, cal, out


summaries = []
calibration_tables = {}

for col in candidate_cols:
    summary, cal, out = score_predictor(
        d,
        x_col=col,
        y_col=Y_COL,
        target_seconds=TARGET_SECONDS,
        n_splits=5,
    )

    summaries.append(summary)
    calibration_tables[col] = cal

comparison = pd.DataFrame(summaries)

# Sort by Brier score first because this is for probability maps.
comparison = comparison.sort_values(["brier", "log_rmse"]).reset_index(drop=True)

print("MODEL COMPARISON")
print(comparison.to_string(index=False))

print("\nBest predictor by Brier score:")
print(comparison.iloc[0]["predictor"])

print("\nBest predictor by log RMSE:")
print(comparison.sort_values("log_rmse").iloc[0]["predictor"])

print("\nBest predictor by p90 calibration closest to 0.900:")
print(
    comparison.iloc[
        comparison["p90_error_from_0.90"].abs().argsort().iloc[0]
    ]["predictor"]
)

# Print calibration tables for each model.
for col in candidate_cols:
    print(f"\nCALIBRATION TABLE FOR {col}")
    print(calibration_tables[col])
