IN ORDER TO BUILD OSRM DATA FILES

need data directory
need .osm map in data directory

check config file

BUILD MAP: docker compose run --rm prepare

docker compose up -d   == START SERVER
docker compose down   == STOP SERVER

TEST SF: curl "http://localhost:5000/match/v1/driving/-122.4194,37.7749;-122.4180,37.7760"
