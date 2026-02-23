"""Sensor platform for Flora Planner."""
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ZONE_NAME, ATTR_WEEKLY_STORY, CONF_PLANTS
from . import FloraPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flora Planner sensor platform."""
    coordinator: FloraPlannerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities(
        [WeeklyStorySensor(coordinator, config_entry)],
        update_before_add=True,
    )


class WeeklyStorySensor(CoordinatorEntity, SensorEntity):
    """A sensor that provides a weekly, AI-generated story for garden tasks."""

    _attr_icon = "mdi:book-open-page-variant"

    def __init__(self, coordinator: FloraPlannerCoordinator, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_name = config_entry.data[CONF_ZONE_NAME]
        self._attr_name = f"Flora Planner {self._zone_name} Weekly Story"
        self._attr_unique_id = f"{config_entry.entry_id}_weekly_story"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.data:
            story = self.coordinator.data.get(ATTR_WEEKLY_STORY)
            return "Beschikbaar" if story else "Geen verhaal"
        return "Wachten op data..."

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = {}
        if self.coordinator.data:
            attributes["full_story"] = self.coordinator.data.get(ATTR_WEEKLY_STORY, "Nog geen verhaal gegenereerd.")
            
            # Voeg details van alle planten toe zodat je ze op het dashboard kunt zien
            plants = self.coordinator.config_entry.options.get(CONF_PLANTS, [])
            plant_details = []
            for plant in plants:
                detail = {
                    "naam": plant.get("plant_name"),
                    "water_interval": plant.get("watering_interval"),
                    "min_vochtigheid": plant.get("min_moisture"),
                    "bodem_sensor": plant.get("soil_moisture_entity"),
                    "huidige_vochtigheid": "Onbekend"
                }
                if detail["bodem_sensor"]:
                    state = self.hass.states.get(detail["bodem_sensor"])
                    if state:
                        detail["huidige_vochtigheid"] = state.state
                plant_details.append(detail)
            
            attributes["planten_lijst"] = plant_details
            
        return attributes
