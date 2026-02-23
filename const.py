"""Constants for the Flora Planner integration."""
from typing import Final

DOMAIN: Final = "flora_planner"

# Config Flow
CONF_GEMINI_API_KEY: Final = "gemini_api_key"
CONF_ZONE_NAME: Final = "zone_name"
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_SPRINKLER_ENTITY: Final = "sprinkler_entity"
CONF_CYCLE_MINUTES: Final = "cycle_minutes"
CONF_SOAK_MINUTES: Final = "soak_minutes"
CONF_MAX_CYCLES: Final = "max_cycles"
CONF_PLANTS: Final = "plants"
CONF_PLANT_NAME: Final = "plant_name"
CONF_USE_AI: Final = "use_ai"
CONF_WATER_INTERVAL: Final = "watering_interval"
CONF_FEED_INTERVAL: Final = "feeding_interval"
CONF_WATER_START_MONTH: Final = "water_start_month"
CONF_WATER_END_MONTH: Final = "water_end_month"
CONF_FEED_START_MONTH: Final = "feed_start_month"
CONF_FEED_END_MONTH: Final = "feed_end_month"
CONF_PRUNE_MONTH: Final = "pruning_month"
CONF_SOW_MONTH: Final = "sowing_month"
CONF_HARVEST_MONTH: Final = "harvesting_month"
CONF_ANCHOR_DATE: Final = "anchor_date"
CONF_SOIL_MOISTURE_ENTITY: Final = "soil_moisture_entity"
CONF_MIN_MOISTURE: Final = "min_moisture"
CONF_DROUGHT_ONLY: Final = "drought_only"

# Weather & Soil Logic
TEMP_THRESHOLD: Final = 28  # Celsius
PRECIP_THRESHOLD: Final = 5  # mm
SOIL_MOISTURE_THRESHOLD: Final = 20 # Percent

# Platforms
PLATFORMS: Final = ["sensor", "binary_sensor", "calendar", "switch"]

# Events
EVENT_WATER = "water"
EVENT_FEED = "feed"
EVENT_PRUNE = "prune"
EVENT_SOW = "sow"
EVENT_HARVEST = "harvest"

# Attributes & State
ATTR_WATERING_REQUIRED = "watering_required"
ATTR_LAST_WATERED = "last_watered"
ATTR_NEXT_WATERING = "next_watering"
ATTR_DYNAMIC_INTERVAL = "dynamic_watering_interval"
ATTR_WEEKLY_STORY = "weekly_story"
