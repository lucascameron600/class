import geopandas as gpd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import random

from osrm import OSRM
from Emergent_vis import HOSPITALS
from shapely.geometry import Point ##geopandas
from pyrosm import OSM


print('OPENING PBF')
INIT = OSM('../data/SF_dp.osm.pbf', workers='auto')
print('OPEN')

DEFAULT_SPEED = 20
#Syntheic baseline generator? research that
#def calculate_region_historical_averagespeed(region, time_band): query backend
#def calculate_edge_timecost_multiplier(edge, time_band):
#def sum_timecosts_penalites(): left turns, right turns, U-turns, Railroads
#def sum_timecosts_djisktra(multiplier, time, penalties):

##def sum_edge_lengths
##def sum_static_costs(edge,):

##def pull_current_traffic_data():
##def pull_hospital_registry():
    ##plan to hard code all values for now, later can sort pulling from registry to update,

##returning nodes, edges from network, driving only
#TAGS_TO_KEEP = ["highway","maxspeed","oneway",]
##FILTERING STAGE
print('EXTRACTING GRAPH')
NODES, EDGES = INIT.get_network(network_type='driving', nodes=True)
print("drivable roads in the network")

#drop nas looking at max speeds
print(EDGES["maxspeed"].value_counts(dropna=False))
EDGES["maxspeed"] = (EDGES["maxspeed"].astype(str).str.extract("([0-9]+)")[0].astype("float64"))
EDGES["maxspeed"].unique()




def build_stations_geo():
    ##geoframe built for geospacial analysis
    STATION_ROWS = []

    for hospital, lat, lon, designation in HOSPITALS:
        HOSPITAL_ROWS.append({"name": hospital, "trauma_designation": designation, "point": Point(lon, lat),})

    HOSPITALS_GEOFRAME = gpd.GeoDataFrame(HOSPITAL_ROWS, geometry="point", crs="EPSG:4326") #lat,lon measured in degrees
    return HOSPITALS_GEOFRAME

HOSPITALS_GEOFRAME = build_stations_geo()


#build network x graph. directional, multigraph
BUILT_GRAPH = INIT.to_graph(NODES, EDGES, graph_type="networkx")
#^^simplify=True to remove degree 2 interstitial nodes(irrelevant turn nodes)
#geo pandas filter nodes after simplification only
#SIMP_NODES = NODES[NODES['id'].isin(BUILT_GRAPH.nodes)]



##access = emergency = shortcut route for an ambulance,  need to make sure these are included to mitigate error in "point of no return" edges.
##directed and, even in emergency setting.  geographically isolated "time traps". EMS does not oppose traffic on those roads typically.
## CHP collects data and they are very relevant here, CHP keeps very very strict control over major california roads.
##EMS in CCEMSA typically has limiter on sprinter van type ambulances. source further EMS speed data??

## in a more urban setting than ccemsa , how do these shortcut roads look??
##what are the challenges of those more urban settings? where are these roads besides freeway?
em_access_tags = EDGES['access'] == 'emergency'
em_edges = EDGES[em_access_tags]
print('tags with emergency access')
print(em_edges.head(20))


#project to albers for best CA geospacial math
EDGES_proj_albers = EDGES.to_crs("EPSG:6422")#6422 for fresno
NODES_proj_albers = NODES.to_crs("EPSG:6422")
hospitals_proj = HOSPITALS_GEOFRAME.to_crs("EPSG:6422")


#quick snap, hospital nodes to nearest, includes distance to snapped node
snap_hospitals = gpd.sjoin_nearest(hospitals_proj, NODES_proj_albers, distance_col="distance")
snapped_hospital_ids = snap_hospitals["id"].tolist()
print(snap_hospitals)



##print(list(BUILT_GRAPH.edges(data=True))[1])
##REVERSED_GRAPH = BUILT_GRAPH.reverse(copy=False)
##print(list(REVERSED_GRAPH.edges(data=True))[1])

##EDGE time COSTS in MINUTES
#time per node with edge, do we get an infinite coastline type of thing with an unsimplified graph??? test
for start_node, end_node, identifier, edge_data in BUILT_GRAPH.edges(keys=True, data=True):
    length_ = edge_data.get("length")
###in progress add road_speed_weight and sort default speeds
##before that, add turn costs, consider U-turn.
    if length_ is not None and not np.isnan(length_):
        edge_data['driving_time'] = (length_ / 1609.34) / DEFAULT_SPEED * 60 #meters to minutes
    else:
        print('missing length')

##account for turns, 10 secs left, 5 right
##time dependent weights, implement
##look at historical speed profile(historical speed bins to caluclate speed instead ), look at congestion multiplier,
##graph must be reversed before costs are calculated,


##turn costs

print('sum min total costs to all paths')
multi_source_costs = nx.multi_source_dijkstra_path_length(BUILT_GRAPH, snapped_hospital_ids, weight="driving_time", cutoff=10) #cutoff in minutes

print(HOSPITALS_GEOFRAME)

for i in list(multi_source_costs.items())[:5]:
    print(i)

#np.array()?
#get nodes and times
node_ids = list(multi_source_costs.keys())
travel_times = list(multi_source_costs.values())
print('coords')

#coords
final_coords = NODES_proj_albers.set_index("id").loc[node_ids]

##print(list(final_coords.id.values[1]))
final_xcoords = final_coords.geometry.x.values
final_ycoords = final_coords.geometry.y.values
# stacking nodes??


##def times_from_nearest:

#plotting
fig, ax = plt.subplots(figsize=(35, 35))
scatterdots = ax.scatter(final_xcoords, final_ycoords, c=travel_times, rasterized=True, cmap="summer", s=.2, vmax=10, alpha=0.7) #vmax = 60 minute cost, max displayed dots
ax.set_aspect('equal')
plt.title('Travel time from station')
p = Point(-119.8051, 36.7857)
gdf = gpd.GeoDataFrame(geometry=[p], crs="EPSG:4326").to_crs("EPSG:6422") #EPSG:6422 for fresno county

ax.plot(gdf.geometry.x, gdf.geometry.y, 'ko', markersize=6, zorder=5)
#plt.show()
#nx.draw(final_coords)
plt.savefig("outcome/travel_time_mvp_fire.png", dpi=600)

