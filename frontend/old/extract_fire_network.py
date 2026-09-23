import os
import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from pyrosm import OSM

# ---------------- CONFIG: edit these to match your setup ----------------
PBF_PATH = '../../data/osm/norcal.osm.pbf'   # NorCal extract in the sibling folder
STATIONS_PARQ = '../../data/workingfiles/stations/post_et_sf_stations.parquet'

# column names in firestations.parq
NAME_COL = 'station_id'
LAT_COL = 'station_latitude'
LON_COL = 'station_longitude'

PROJ_CRS = 'EPSG:3310'     # California Albers (meters), valid statewide incl. SF
DEFAULT_SPEED = 20         # mph
CUTOFF_MIN = 10            # dijkstra cutoff in minutes
BBOX_PAD_DEG = 0.02        # ~2 km of road network kept around the outermost stations
OUT_PNG = 'outcome/travel_time_sf_fire.png'
# -------------------------------------------------------------------------

##def calculate_region_historical_averagespeed(region, time_band): query backend
##def calculate_edge_timecost_multiplier(edge, time_band):
##def sum_timecosts_penalites(): left turns, right turns, U-turns, Railroads
##def sum_timecosts_djisktra(multiplier, time, penalties):


def build_stations_geo(parq_path):
    ##geoframe built for geospacial analysis one row per station
    df = pd.read_parquet(parq_path)
    df = df.dropna(subset=[LAT_COL, LON_COL, NAME_COL])

    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[LON_COL], df[LAT_COL]),  # x = lon, y = lat
        crs='EPSG:4326',
    )


STATIONS_GEOFRAME = build_stations_geo(STATIONS_PARQ)
print(f'loaded {len(STATIONS_GEOFRAME)} stations')

# clip the NorCal extract to a box around the stations so we don't load all of NorCal
minx, miny, maxx, maxy = STATIONS_GEOFRAME.total_bounds
BBOX = [minx - BBOX_PAD_DEG, miny - BBOX_PAD_DEG, maxx + BBOX_PAD_DEG, maxy + BBOX_PAD_DEG]

print('OPENING PBF')
INIT = OSM(PBF_PATH, bounding_box=BBOX)
print('OPEN')

print('EXTRACTING GRAPH')
NODES, EDGES = INIT.get_network(network_type='driving', nodes=True)
print('drivable roads in the network')

print(EDGES['maxspeed'].value_counts(dropna=False))
EDGES['maxspeed'] = EDGES['maxspeed'].astype(str).str.extract(r'([0-9]+)')[0].astype('float64')

##access = emergency = shortcut routes, keep an eye on these in the urban setting too
if 'access' in EDGES.columns:
    em_edges = EDGES[EDGES['access'] == 'emergency']
    print(f'{len(em_edges)} edges tagged access=emergency')
    print(em_edges.head(20))

#build network x graph. directional, multigraph
BUILT_GRAPH = INIT.to_graph(NODES, EDGES, graph_type='networkx')
#SIMPLIFY = = TRUE TO REMOVE INTERSTITIAL D2 NODES ^^^

#project for geospatial math
NODES_proj = NODES.to_crs(PROJ_CRS)
stations_proj = STATIONS_GEOFRAME.to_crs(PROJ_CRS)




# snap stations only to nodes that actually made it into the graph,
# otherwise dijkstra can fail with NodeNotFound
graph_nodes = (
    NODES_proj.loc[NODES_proj['id'].isin(BUILT_GRAPH.nodes), ['id', 'geometry']]
    .rename(columns={'id': 'node_id'})   # avoids clashing with an 'id' column in the CSV
)
snap_stations = gpd.sjoin_nearest(stations_proj, graph_nodes, distance_col='snap_dist_m')
snap_stations = snap_stations[~snap_stations.index.duplicated()]   # ties can duplicate rows
snapped_station_ids = snap_stations['node_id'].unique().tolist()

far = snap_stations[snap_stations['snap_dist_m'] > 200]
if len(far):
    print('WARNING: these stations snapped more than 200 m from a road node, check their coords:')
    print(far[[c for c in (NAME_COL, 'snap_dist_m') if c in far.columns]])

##EDGE time COSTS in MINUTES
for start_node, end_node, identifier, edge_data in BUILT_GRAPH.edges(keys=True, data=True):
    length_ = edge_data.get('length')
    if length_ is not None and not np.isnan(length_):
        edge_data['driving_time'] = (length_ / 1609.34) / DEFAULT_SPEED * 60  # meters to minutes
    else:
        print('missing length')

##turn costs, time dependent weights, historical speed bins: TODO
## no graph reversal needed here: fire response is station -> incident, which is
## the graph's forward direction (hospital transport was incident -> hospital)

print('sum min total costs to all paths')
multi_source_costs = nx.multi_source_dijkstra_path_length(
    BUILT_GRAPH, snapped_station_ids, weight='driving_time', cutoff=CUTOFF_MIN
)

node_ids = list(multi_source_costs.keys())
travel_times = list(multi_source_costs.values())
final_coords = NODES_proj.set_index('id').loc[node_ids]

#plotting
fig, ax = plt.subplots(figsize=(35, 35))
scatterdots = ax.scatter(
    final_coords.geometry.x.values, final_coords.geometry.y.values,
    c=travel_times, rasterized=True, cmap='summer', s=.2, vmax=CUTOFF_MIN, alpha=0.7,
)
stations_proj.plot(ax=ax, color='red', marker='^', markersize=120, zorder=5)
if NAME_COL in stations_proj.columns:
    for _, row in stations_proj.iterrows():
        ax.annotate(str(row[NAME_COL]), (row.geometry.x, row.geometry.y),
                    xytext=(4, 4), textcoords='offset points', fontsize=10)

fig.colorbar(scatterdots, ax=ax, shrink=0.5, label='minutes from nearest station')
ax.set_aspect('equal')
plt.title('Travel time from nearest SF fire station')

os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
plt.savefig(OUT_PNG, dpi=600, bbox_inches='tight')
print(f'saved {OUT_PNG}')



