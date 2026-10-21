"""Constants for the Västtrafik M34 integration."""

DOMAIN = "vasttrafik_m34"

TOKEN_URL = "https://ext-api.vasttrafik.se/token"
API_BASE = "https://ext-api.vasttrafik.se/pr/v4"

# Config entry data keys
CONF_AUTH_KEY = "auth_key"
CONF_STATION_GID = "station_gid"
CONF_STATION_NAME = "station_name"

# Options
CONF_DIRECTION_FILTER = "direction_filter"
CONF_LINE_FILTER = "line_filter"
CONF_EXCLUDE_CANCELLED = "exclude_cancelled"
CONF_SHOW_DELAY = "show_delay"
CONF_TIME_SPAN_MINUTES = "time_span_minutes"
CONF_MAX_PER_LINE = "max_per_line"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_EXCLUDE_CANCELLED = True
DEFAULT_SHOW_DELAY = False
DEFAULT_TIME_SPAN_MINUTES = 90
DEFAULT_MAX_PER_LINE = 4
DEFAULT_UPDATE_INTERVAL = 60  # seconds

ATTR_DEPARTURES = "departures"
ATTR_DEPARTURES_JSON = "departures_json"
ATTR_DEPARTURE_COUNT = "departure_count"
ATTR_LAST_UPDATE = "last_update"
ATTR_NEXT_LINE = "next_line"
ATTR_NEXT_DESTINATION = "next_destination"
ATTR_NEXT_DEPARTURE_TIME = "next_departure_time"
ATTR_NEXT_MINUTES_UNTIL = "next_minutes_until"
ATTR_NEXT_TRACK = "next_track"
ATTR_NEXT_DELAY_MINUTES = "next_delay_minutes"
ATTR_NEXT_IS_REALTIME = "next_is_realtime"
ATTR_STATION_GID = "station_gid"
ATTR_STATION_NAME = "station_name"
ATTR_DIRECTION_FILTER = "direction_filter"
ATTR_LINE_FILTER = "line_filter"
