-- LUKES CUSTOM SF code 3 fire engine profile
-- Derived from the stock OSRM car profile
--
-- changes from stock  car.lua:
--
--   ACCESS   wil use any road a motor vehicle can physically drive, bus/taxi/any impt for SF
--            tested on market street
--            emergency-access roads, HOV, motorcar=no is good too
--
--            private roads get a small entry penalty instead of the
--            --no footways or any path that wont be drivable
--
--   ONEWAYS  never drives against traffic, on any road. Bus/psv exemptions
--            (oneway:bus=no, oneway:psv=no) are ignored so bus-only lanes that
--            run against traffic stay one-way for the engine.
--
--
--   TURNS    turn restrictions apply, except ones exempting buses/taxis/psv/emergency.
--
--   SPEEDS   code 3 speeds set to be updated by stan. MAXSPEED tags are ignored through this profile
--
--   VEHICLE  average engine dimensions. bigger turn and u turn penalties.

api_version = 4

Set = require('lib/set')
Sequence = require('lib/sequence')
Handlers = require("lib/way_handlers")
Relations = require("lib/relations")
Obstacles = require("lib/obstacles")
find_access_tag = require("lib/access").find_access_tag
resolve_access = require("lib/access").resolve_access
limit = require("lib/maxspeed").limit
Utils = require("lib/utils")
Measure = require("lib/measure")

function setup()
  return {
    properties = {
      max_speed_for_map_matching      = 180/3.6, -- 180kmph -> m/s
        --tried duration worked good but too fast needed custom
      weight_name                     = 'routability',

      process_call_tagless_node      = false,
      u_turn_penalty                 = 120,  -- u turn impossible for engine in sf
      continue_straight_at_waypoint  = true,
      use_turn_restrictions          = true,
    },

    default_mode              = mode.driving,
    default_speed             = 10,
    oneway_handling           = true,
    side_road_multiplier      = 0.8,
    turn_penalty              = 12,     -- long wheelbase on these guys have u tried to turn one of these before?
    speed_reduction           = 0.8,    -- unused now
    turn_bias                 = 1.075,
    oncoming_turn_penalty     = 1.0,    -- traffic yields to a code 3 turn NEW
    cardinal_directions       = false,

    lane_markings_penalty     = 0.75,
    priority_penalty          = 0.7,

    -- route choice is extremely important here, this will effect what route the
    -- engine chooses, still trying to tune these but this is based soley off exeperience
    -- and my estimation of how a fire engine drives.
    class_preference = {
      tertiary = 0.9, unclassified = 0.75, residential = 0.7,
      living_street = 0.5, service = 0.5
    },


    -- Code 3 NEW
    ---------------------------------------------------------------------------

    -- Seconds of routing weight for entering a private/destination/etc. road.
    -- Stock car.lua uses max_turn_weight here, which walls those roads off.
    restricted_entry_penalty  = 30,

    ---------
    -- Vehicle: ENGINE
    ---------------------------------------------------------------------------
    vehicle_height = 3.3,     -- m
    vehicle_width  = 2.5,
    vehicle_length = 10.5,
    vehicle_weight = 19000,   -- kg
    vehicle_max_speed = 88,   -- km/h GOVERNED speed

    suffix_list = {
      'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'North', 'South', 'West', 'East', 'Nor', 'Sou', 'We', 'Ea'
    },

    barrier_whitelist = Set {
      'cattle_grid',
      'border_control',
      'toll_booth',
      'sally_port',
      'no',
      'entrance',
      'height_restrictor',
      'arch'
    },

    access_tag_whitelist = Set {
      'yes',
      'emergency',
      'psv',
      'bus',
      'taxi',
      'motorcar',
      'motor_vehicle',
      'vehicle',
      'permissive',
      'designated',
      'hov'
    },

    -- Only values that truly keep an engine out. Transit/emergency/official
    -- values were removed: an engine can use those roads.
    access_tag_blacklist = Set {
      'no',
      'agricultural',
      'forestry',
      'foot',
      'military'
    },

    service_access_tag_blacklist = Set {
        'private'
    },

    -- Usable, but entering costs restricted_entry_penalty.
    restricted_access_tag_list = Set {
      'private',
      'delivery',
      'destination',
      'customers',
      'permit',
      'residents',
      'unknown',
      'restricted'
    },

    -- motorcar dropped: an engine isn't a motorcar in OSM terms.
    -- psv/bus/taxi are handled by engine_access below, not here, so that
    -- bus=no on a street can't lock the engine out.
    access_tags_hierarchy = Sequence {
      'emergency',
      'motor_vehicle',
      'vehicle',
      'access'
    },

    -- emergency_access roads are exactly what we want
    service_tag_forbidden = Set {
    },

    -- OSRM skips restrictions when its except= has one of these
    -- no left turn unless busses or engines, this heirarchy avoids that
    -- for handling once ways, does not use this
    restrictions = Sequence {
      'emergency',
      'psv',
      'bus',
      'taxi',
      'motor_vehicle',
      'vehicle'
    },

    classes = Sequence {
        'toll', 'motorway', 'ferry', 'restricted', 'tunnel'
    },

    excludable = Sequence {
        Set {'toll'},
        Set {'motorway'},
        Set {'ferry'}
    },

    avoid = Set {
      'area',
      'reversible',
      'impassable',
      'steps',
      'construction',
      'proposed'
    },

    --starting points for SF, need to calibrate these later
    -- in kmph
    speeds = Sequence {
      highway = {
        motorway        = 85,
        motorway_link   = 45,
        trunk           = 52,
        trunk_link      = 35,
        primary         = 50,
        primary_link    = 30,
        secondary       = 44,
        secondary_link  = 25,
        tertiary        = 38,
        tertiary_link   = 20,
        unclassified    = 28,
        residential     = 28,
        living_street   = 10,
        service         = 15
      }
    },

    service_penalties = {
      alley             = 0.5,
      parking           = 0.5,
      parking_aisle     = 0.5,
      driveway          = 0.5,
      ["drive-through"] = 0.5,
      ["drive-thru"] = 0.5
    },

    barrier_penalties = {
      gate      = 60,
      lift_gate = 60,
    },

    restricted_highway_whitelist = Set {
      'motorway',
      'motorway_link',
      'trunk',
      'trunk_link',
      'primary',
      'primary_link',
      'secondary',
      'secondary_link',
      'tertiary',
      'tertiary_link',
      'residential',
      'living_street',
      'unclassified',
      'winter_road',
      'ice_road', --we got ice roads in sf?
      'service'
    },

    construction_whitelist = Set {
      'no',
      'widening',
      'minor',
    },

    route_speeds = {
      ferry = 5,
      shuttle_train = 10
    },

    bridge_speeds = {
    },

    surface_speeds = {
      cement = 80,
      compacted = 80,
      fine_gravel = 80,

      paving_stones = 60,
      metal = 60,
      bricks = 60,

      grass = 40,
      wood = 40,
      sett = 40,
      grass_paver = 40,
      gravel = 40,
      unpaved = 40,
      ground = 40,
      dirt = 40,
      pebblestone = 40,
      tartan = 40,

      cobblestone = 30,
      clay = 30,

      earth = 20,
      stone = 20,
      rocky = 20,
      sand = 20,

      ice =20,
      snow =30,

      laterite = 15,
      mud = 10
    },

    tracktype_speeds = {
      grade1 =  60,
      grade2 =  40,
      grade3 =  30,
      grade4 =  25,
      grade5 =  20
    },

    smoothness_speeds = {
      intermediate    =  80,
      bad             =  40,
      very_bad        =  20,
      horrible        =  10,
      very_horrible   =  5,
      impassable      =  0
    },

    -- maxspeed handler is not used
    maxspeed_table_default = {
      urban = 50,
      rural = 90,
      trunk = 110,
      motorway = 130
    },

    maxspeed_table = {
      ["none"] = 140
    },

    relation_types = Sequence {
      "route"
    },

    highway_turn_classification = {
    },

    access_turn_classification = {
    }
  }
end


---------------------
-- Code 3 helpers----
---------------------
local POSITIVE = Set { 'yes', 'designated', 'permissive' }
local NO_MODES = Sequence {}

-- becomes true when tags admit emergency vehicles, or (with no emergency
-- works for ways and nodes.
local function engine_allowed(obj)
  local e = obj:get_value_by_key('emergency')
  if e then
    return POSITIVE[e] == true   -- emergency=no falls through to normal checks, which block it
  end
  for _, key in ipairs({ 'psv', 'bus', 'taxi', 'hov' }) do
    if POSITIVE[obj:get_value_by_key(key)] then
      return true
    end
  end
  return false
end

-- Only real roadway types. Keeps footways, platforms, busways, tracks and
-- ferries out even when they carry emergency=yes or bus=yes.
local function highway_filter(profile, way, result, data)
  if not profile.speeds.highway[data.highway] then
    result.forward_mode = mode.inaccessible
    result.backward_mode = mode.inaccessible
    return false
  end
end

--  if any type of vehicle can access this road than so can the fire engine
local function engine_access(profile, way, result, data)
  if engine_allowed(way) then
    data.forward_access, data.backward_access = 'yes', 'yes'
    return
  end
  return WayHandlers.access(profile, way, result, data)
end

-- Stock oneway handling, but ignoring mode exemptions (oneway:bus=no,
-- oneway:psv=no, ...) so bus-only lanes against traffic stay one-way for the engine.
-- Safe: turn restrictions read profile.restrictions once at setup, and each
-- OSRM thread has its own Lua state.
local function strict_oneway(profile, way, result, data)
  local saved = profile.restrictions
  profile.restrictions = NO_MODES
  local r = WayHandlers.oneway(profile, way, result, data)
  profile.restrictions = saved
  return r
end

-- Prefer arterials over cutting through neighborhoods (route choice only).
local function arterial_preference(profile, way, result, data)
  local pref = profile.class_preference[data.highway]
  if pref then
    if result.forward_rate > 0 then result.forward_rate = result.forward_rate * pref end
    if result.backward_rate > 0 then result.backward_rate = result.backward_rate * pref end
  end
end

-------------------------------------------------------------------------------

function process_node(profile, node, result, relations)
  local barrier = node:get_value_by_key("barrier")

  -- Bus gates, emergency-only bollards, etc. Height limits still apply.
  if barrier ~= 'height_restrictor' and engine_allowed(node) then
    Obstacles.process_node(profile, node)
    return
  end

  -- parse access and barrier tags
  local access = resolve_access(find_access_tag(node, profile.access_tags_hierarchy), profile)
  if access then
    if profile.access_tag_blacklist[access] and not profile.restricted_access_tag_list[access] then
      obstacle_map:add(node, Obstacle.new(obstacle_type.barrier))
    end
  else
    if barrier then
      --  check height restriction barriers
      local restricted_by_height = false
      if barrier == 'height_restrictor' then
         local maxheight = Measure.get_max_height(node:get_value_by_key("maxheight"), node)
         restricted_by_height = maxheight and maxheight < profile.vehicle_height
      end

      --  make an exception for rising bollard barriers
      local bollard = node:get_value_by_key("bollard")
      local rising_bollard = bollard and "rising" == bollard

      -- make an exception for lowered/flat barrier=kerb
      -- and incorrect tagging of highway crossing kerb as highway barrier
      local kerb = node:get_value_by_key("kerb")
      local highway = node:get_value_by_key("highway")
      local flat_kerb = kerb and ("lowered" == kerb or "flush" == kerb)
      local highway_crossing_kerb = barrier == "kerb" and highway and highway == "crossing"

      -- make an exception for fence with sensory=audible/audio (virtual livestock fences)
      local sensory = node:get_value_by_key("sensory")
      local audible_fence = barrier == "fence" and sensory and (sensory == "audible" or sensory == "audio")

      -- check if barrier has a configurable penalty (e.g., gates)
      local barrier_penalty = profile.barrier_penalties[barrier]

      if not profile.barrier_whitelist[barrier]
                and not rising_bollard
                and not flat_kerb
                and not highway_crossing_kerb
                and not audible_fence
                and not barrier_penalty
                or restricted_by_height then
        obstacle_map:add(node, Obstacle.new(obstacle_type.barrier))
      end

      -- apply configurable penalty to gates/lift_gates
      if barrier_penalty then
        obstacle_map:add(node, Obstacle.new(obstacle_type.gate,
                                            obstacle_direction.both, barrier_penalty, 0))
      end
    end
  end

  Obstacles.process_node(profile, node)
end

function process_way(profile, way, result, relations)
  local data = {
    highway = way:get_value_by_key('highway'),
    bridge = way:get_value_by_key('bridge'),
    route = way:get_value_by_key('route')
  }

  if (not data.highway or data.highway == '') and
  (not data.route or data.route == '')
  then
    return
  end

  handlers = Sequence {
    highway_filter,                 -- true drivable roads only
    WayHandlers.default_mode,

    WayHandlers.blocked_ways,
    WayHandlers.avoid_ways,
    WayHandlers.handle_height,
    WayHandlers.handle_width,
    WayHandlers.handle_length,
    WayHandlers.handle_weight,

    engine_access,                  -- replace WayHandlers.access
    strict_oneway,                  -- replace WayHandlers.oneway

    WayHandlers.destinations,

    -- ferries/movables removed: no ferries on a response, and the movable
    -- bridge handler resets both directions to drivable (overriding oneway)

    WayHandlers.service,
    WayHandlers.hov,

    WayHandlers.speed,


    -- WayHandlers.maxspeed removed: Code 3 speed comes from road class, not posted limits
    --
    --
    WayHandlers.surface,
    WayHandlers.vehicle_speed_cap,

    WayHandlers.penalties,
    arterial_preference,

    WayHandlers.classes,
    WayHandlers.turn_lanes,
    WayHandlers.classification,
    WayHandlers.roundabouts,
    WayHandlers.startpoint,
    WayHandlers.driving_side,
    WayHandlers.names,
    WayHandlers.weights,

    WayHandlers.way_classification_for_turn
  }

  WayHandlers.run(profile, way, result, data, handlers, relations)

  if profile.cardinal_directions then
      Relations.process_way_refs(way, relations, result)
  end
end

function process_turn(profile, turn)
  local turn_penalty = profile.turn_penalty
  local turn_bias = turn.is_left_hand_driving and 1. / profile.turn_bias or profile.turn_bias

  for _, obs in pairs(obstacle_map:get(turn.from, turn.via)) do
    if obs.type == obstacle_type.stop_minor and not Obstacles.entering_by_minor_road(turn) then
        goto skip
    end
    if turn.number_of_roads == 2
        and obs.type == obstacle_type.stop
        and obs.direction == obstacle_direction.none
        and turn.source_road.distance < 20
        and turn.target_road.distance > 20 then
            goto skip
    end
    turn.duration = turn.duration + obs.duration
    ::skip::
  end

  if turn.number_of_roads > 2 or turn.source_mode ~= turn.target_mode or turn.is_u_turn then
    if turn.angle >= 0 then
      turn.duration = turn.duration + turn_penalty / (1 + math.exp( -((13 / turn_bias) *  turn.angle/180 - 6.5*turn_bias)))
    else
      turn.duration = turn.duration + turn_penalty / (1 + math.exp( -((13 * turn_bias) * -turn.angle/180 - 6.5/turn_bias)))
    end

    local crosses_oncoming
    if turn.is_left_hand_driving then
      crosses_oncoming = turn.angle > 0
    else
      crosses_oncoming = turn.angle < 0
    end

    if crosses_oncoming and not turn.is_u_turn and turn.number_of_roads > 2
       and not turn.source_is_roundabout and not turn.target_is_roundabout then
      local sharpness = 1 / (1 + math.exp( -(13 * math.abs(turn.angle)/180 - 3.25)))
      turn.duration = turn.duration + profile.oncoming_turn_penalty * sharpness
    end

    if turn.is_u_turn then
      turn.duration = turn.duration + profile.properties.u_turn_penalty
    end
  end

  if profile.properties.weight_name == 'distance' then
     turn.weight = 0
  else
     turn.weight = turn.duration
  end

  if profile.properties.weight_name == 'routability' then
    -- Finite penalty for entering private/destination roads (stock: max_turn_weight wall)
    if not turn.source_restricted and turn.target_restricted then
      turn.weight = turn.weight + profile.restricted_entry_penalty
    end

  end
end

return {
  setup = setup,
  process_way = process_way,
  process_node = process_node,
  process_turn = process_turn
}
