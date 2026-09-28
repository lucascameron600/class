-- LUKES CUSTOM SF code 3 engine profile
-- 
-- Changes to code detailed here
-- 
-- SETTINGS, changes to settings detailed by code that was changed
--          mostly updated simple things like weight default speed etc.
--
--
--

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
      
        -- tried duration, was pretty good but need more control
        -- over true routes
      weight_name                     = 'routability',
      

      process_call_tagless_node      = false,
      u_turn_penalty                 = 120,  --need high uturn penalty on engines, prob higher on ladder trucks
      continue_straight_at_waypoint  = true,
      use_turn_restrictions          = true,
    },


    default_mode              = mode.driving,
    default_speed             = 10,
    oneway_handling           = true,
    side_road_multiplier      = 0.8,
    turn_penalty              = 12, --long wheelbase on these guys, you tried turning an engine in SF??
    
    speed_reduction           = 0.8, --unused
    turn_bias                 = 1, --neutral turn bias, need to get to call.
    oncoming_turn_penalty     = 2.0, --will replace this with lane clearing
    cardinal_directions       = false,

    lane_markings_penalty     = 0.75,
    priority_penalty          = 0.7,

    class_preference = {tertiary = 0.9, unclassified = 0.75,
                        residential = 0.7, living_street = 0.5,
                        service = 0.5},


    ------------------------------------------------------------------
    ---- VEHICLE -> SF ENGINE
    ---------------------------

    vehicle_height = 3.3, -- in meters, 2.0m is the height slightly above biggest SUVs
    vehicle_width = 2.5, -- in meters, ways with narrow tag are considered narrower than 2.2m
    vehicle_length = 10.5, -- in meters, 4.8m is the length of large or family car
    vehicle_weight = 19000, -- in kilograms
    vehicle_max_speed = 88, -- CHECK THIS, GOVERNOR??

    ---------------------------------------------------------------------------------
    --CODE 3 NEW SETTINGS FOR INTERSECTION CLEARING
    ------------------------------------------------
    --all settings define the number of seconds added
    --to the trip for clearing intersections
    ------------------------------------------------------
    
    clear_signal = 4
    clear_stop = 3
    clear_per_lane = 1.5
    clear_uncotrolled = 0.5

    -- lanes per direction by road class sometimes no lanes=
    lanes_per_direction = {
      motorway = 3, trunk = 2, primary = 2, secondary = 2, tertiary = 1,
      unclassified = 1, residential = 1, living_street = 1, service = 1,
      motorway_link = 1, trunk_link = 1, primary_link = 1, secondary_link = 1, tertiary_link = 1
    },


    -- a list of suffixes to suppress in name change instructions. The suffixes also include common substrings of each other
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
      'emergency', --added
      'psv', --added needed next 3 in sf
      'bus', --added
      'taxi', --added
      'motorcar',
      'motor_vehicle',
      'vehicle',
      'permissive',
      'designated',
      'hov'
    },

    access_tag_blacklist = Set { --removed a lot here, not much can stop an engine w lights
      'no',
      'agricultural',
      'forestry',
      'foot',
      'military',
    },

    -- tags disallow access to in combination with highway=service
    service_access_tag_blacklist = Set {
        'private'
    },

    restricted_access_tag_list = Set {
      'private',
      'restricted', --added
      'delivery',
      'destination',
      'customers',
      'permit',
      'residents',
      'unknown',
    },

    access_tags_hierarchy = Sequence {
      'emergency', --changed from motorcar, emergency gets first priority
      'motor_vehicle',
      'vehicle',
      'access'
    },

    service_tag_forbidden = Set {  --used to have emergency access
    },

    --IMPORTANT FOR PROFILE
    -- OSRM will skip restrictions when except = has one of these
    -- no left turn for busses this avoids that
    restrictions = Sequence {
      'emergency',
      'psv',
      'bus',
      'taxi',
      'motor_vehicle',
      'vehicle'

    classes = Sequence {
        'toll', 'motorway', 'ferry', 'restricted', 'tunnel'
    },

    -- classes to support for exclude flags
    excludable = Sequence {
        Set {'toll'},
        Set {'motorway'},
        Set {'ferry'}
    },

    avoid = Set { --removed hov lane
      'area',
      -- 'toll',    -- uncomment this to avoid tolls
      'reversible',
      'impassable',
      'steps',
      'construction',
      'proposed'
    },
    --starting point for SF, need to "calibrate w real segment speeds"
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
      'service',
      'winter_road',
      'ice_road'
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

    bridge_speeds = { --no bridge
    },

    -- surface/trackype/smoothness
    -- values were estimated from looking at the photos at the relevant wiki pages

    -- max speed for surfaces
    surface_speeds = {
      asphalt = nil,    -- nil mean no limit. removing the line has the same effect
      concrete = nil,
      ["concrete:plates"] = nil,
      ["concrete:lanes"] = nil,
      paved = nil,

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

      laterite = 15,

      mud = 10,

      -- winter surfaces (OSM surface=ice / surface=snow)
      ice  = 20,
      snow = 30
    },

    -- max speed for tracktypes
    tracktype_speeds = {
      grade1 =  60,
      grade2 =  40,
      grade3 =  30,
      grade4 =  25,
      grade5 =  20
    },

    -- max speed for smoothnesses
    smoothness_speeds = {
      intermediate    =  80,
      bad             =  40,
      very_bad        =  20,
      horrible        =  10,
      very_horrible   =  5,
      impassable      =  0
    },

    -- http://wiki.openstreetmap.org/wiki/Speed_limits
    maxspeed_table_default = {
      urban = 50,
      rural = 90,
      trunk = 110,
      motorway = 130
    },

    
    maxspeed_table = { --no longer used here
      ["none"] = 140
    },

    relation_types = Sequence {
      "route"
    },

    -- classify highway tags when necessary for turn weights
    highway_turn_classification = {
    },

    -- classify access tags when necessary for turn weights
    access_turn_classification = {
    }
  }
end

----------------------------------------------------------------------------------------
-- Code 3 helpers
----------------------------------------------------------
local POSITIVE = Set { 'yes', 'designated', 'permissive' }
local NO_MODES = Sequence {}



local function engine_allowed(obj)
  local e = obj:get_value_by_key('emergency')
  if e then
    return POSITIVE[e] == true 
  end
  for _, key in ipairs({ 'psv', 'bus', 'taxi', 'hov' }) do
    if POSITIVE[obj:get_value_by_key(key)] then
      return true
    end
  end
  return false
end

--filters out random road types that were messing w routing
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

-- Stock oneway handling, but ignoring mode exemptions. if a bus can make the turn
-- so can the engine
local function strict_oneway(profile, way, result, data)
  local saved = profile.restrictions
  profile.restrictions = NO_MODES
  local r = WayHandlers.oneway(profile, way, result, data)
  profile.restrictions = saved
  return r
end

-- Lanes per direction for each way, stored in highway_turn_classification so
-- process_turn can count how many lanes of cross traffic must be cleared.
-- Replaces WayHandlers.way_classification_for_turn (whose tables were empty).
local function lanes_for_turn(profile, way, result, data)
  local per_dir = profile.lanes_per_direction[data.highway] or 1
  local lanes = tonumber(way:get_value_by_key('lanes') or '')
  if lanes and lanes > 0 then
    local oneway = way:get_value_by_key('oneway')
    local is_oneway = oneway == 'yes' or oneway == '1' or oneway == 'true' or oneway == '-1'
    per_dir = is_oneway and lanes or math.ceil(lanes / 2)
  end
  result.highway_turn_classification = math.min(math.max(per_dir, 1), 15)  -- OSRM requires < 16
end

-- Prefer arterials over cutting through neighborhoods (route choice only).
local function arterial_preference(profile, way, result, data)
  local pref = profile.class_preference[data.highway]
  if pref then
    if result.forward_rate > 0 then result.forward_rate = result.forward_rate * pref end
    if result.backward_rate > 0 then result.backward_rate = result.backward_rate * pref end
  end
--------------------------------------------------------------------------------

function process_node(profile, node, result, relations)
  -- parse access and barrier tags
  local access = resolve_access(find_access_tag(node, profile.access_tags_hierarchy), profile)
  if access then
    if profile.access_tag_blacklist[access] and not profile.restricted_access_tag_list[access] then
      obstacle_map:add(node, Obstacle.new(obstacle_type.barrier))
    end
  else
    local barrier = node:get_value_by_key("barrier")
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
  -- the intial filtering of ways based on presence of tags
  -- affects processing times significantly, because all ways
  -- have to be checked.
  -- to increase performance, prefetching and intial tag check
  -- is done in directly instead of via a handler.

  -- in general we should  try to abort as soon as
  -- possible if the way is not routable, to avoid doing
  -- unnecessary work. this implies we should check things that
  -- commonly forbids access early, and handle edge cases later.

  -- data table for storing intermediate values during processing
  local data = {
    -- prefetch tags
    highway = way:get_value_by_key('highway'),
    bridge = way:get_value_by_key('bridge'),
    route = way:get_value_by_key('route')
  }

  -- perform an quick initial check and abort if the way is
  -- obviously not routable.
  -- highway or route tags must be in data table, bridge is optional
  if (not data.highway or data.highway == '') and
  (not data.route or data.route == '')
  then
    return
  end

  handlers = Sequence {
    -- set the default mode for this profile. if can be changed later
    -- in case it turns we're e.g. on a ferry
    WayHandlers.default_mode,

    -- check various tags that could indicate that the way is not
    -- routable. this includes things like status=impassable,
    -- toll=yes and oneway=reversible
    WayHandlers.blocked_ways,
    WayHandlers.avoid_ways,
    WayHandlers.handle_height,
    WayHandlers.handle_width,
    WayHandlers.handle_length,
    WayHandlers.handle_weight,

    -- determine access status by checking our hierarchy of
    -- access tags, e.g: motorcar, motor_vehicle, vehicle
    WayHandlers.access,

    -- check whether forward/backward directions are routable
    WayHandlers.oneway,

    -- check a road's destination
    WayHandlers.destinations,

    -- check whether we're using a special transport mode
    WayHandlers.ferries,
    WayHandlers.movables,

    -- handle service road restrictions
    WayHandlers.service,

    -- handle hov
    WayHandlers.hov,

    -- compute speed taking into account way type, maxspeed tags, etc.
    WayHandlers.speed,
    WayHandlers.maxspeed,
    WayHandlers.surface,

    -- apply vehicle-specific maximum speed cap before calculating rates
    WayHandlers.vehicle_speed_cap,

    WayHandlers.penalties,

    -- compute class labels
    WayHandlers.classes,

    -- handle turn lanes and road classification, used for guidance
    WayHandlers.turn_lanes,
    WayHandlers.classification,

    -- handle various other flags
    WayHandlers.roundabouts,
    WayHandlers.startpoint,
    WayHandlers.driving_side,

    -- set name, ref and pronunciation
    WayHandlers.names,

    -- set weight properties of the way
    WayHandlers.weights,

    -- set classification of ways relevant for turns
    WayHandlers.way_classification_for_turn
  }

  WayHandlers.run(profile, way, result, data, handlers, relations)

  if profile.cardinal_directions then
      Relations.process_way_refs(way, relations, result)
  end
end

function process_turn(profile, turn)
  -- Use a sigmoid function to return a penalty that maxes out at turn_penalty
  -- over the space of 0-180 degrees.  Values here were chosen by fitting
  -- the function to some turn penalty samples from real driving.
  local turn_penalty = profile.turn_penalty
  local turn_bias = turn.is_left_hand_driving and 1. / profile.turn_bias or profile.turn_bias

  for _, obs in pairs(obstacle_map:get(turn.from, turn.via)) do
    -- disregard a minor stop if entering by the major road
    -- rationale: if a stop sign is tagged at the center of the intersection with stop=minor
    -- it should only penalize the minor roads entering the intersection
    if obs.type == obstacle_type.stop_minor and not Obstacles.entering_by_minor_road(turn) then
        goto skip
    end
    -- heuristic to infer the direction of a stop without an explicit direction tag
    -- rationale: a stop sign should not be placed farther than 20m from the intersection
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

    -- A turn across oncoming traffic waits for a gap, a turn away from it does
    -- not. turn_bias already leans that way, but it spends itself on the shape
    -- of the sigmoid, so its effect peaks near 90 degrees and fades to almost
    -- nothing at the sharp end, where both branches saturate at turn_penalty.
    -- This term does not fade there.
    --
    -- It only applies where there is oncoming traffic to cross. That means a
    -- real junction, since number_of_roads is also 2 for a mode change or a
    -- compressed obstacle node and charging those would tax every ferry
    -- boarding, and it means neither leg is a roundabout, where traffic runs
    -- one way and going around is a series of turns against nothing. Within a
    -- junction it tapers with the same sigmoid shape as the turn penalty, so a
    -- near-straight manoeuvre pays almost nothing and there is no cliff at the
    -- point where a bend becomes a turn. U-turns are excluded because
    -- u_turn_penalty already pays for crossing traffic through 180 degrees.
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

  -- for distance based routing we don't want to have penalties based on turn angle
  if profile.properties.weight_name == 'distance' then
     turn.weight = 0
  else
     turn.weight = turn.duration
  end

  if profile.properties.weight_name == 'routability' then
      -- penalize turns from non-local access only segments onto local access only tags
      if not turn.source_restricted and turn.target_restricted then
          turn.weight = constants.max_turn_weight
      end
  end
end

return {
  setup = setup,
  process_way = process_way,
  process_node = process_node,
  process_turn = process_turn
}
