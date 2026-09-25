# IN ORDER TO BUILD OSRM DATA FILES

- need data directory
- need .osm map in data directory
- check config file

## BUILD MAP: 
- docker compose run --rm prepare

## START SERVER: 
- docker compose up -d   
- docker compose up -d --force-recreate --remove-orphans

## STOP SERVER: 
- docker compose down   

## TEST SF: 
- curl "http://localhost:5000/match/v1/driving/-122.4194,37.7749;-122.4180,37.7760"

## RERUN NEW MAP: 
- rm data/norcal.osrm.* > BUILD MAP > START SERVER

## GET MAPS: 
- wget -O data/norcal.osm.pbf https://download.geofabrik.de/north-america/us/california/norcal-latest.osm.pbf
