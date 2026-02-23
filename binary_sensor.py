"""Binary sensor for Flora Planner."""
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ZONE_NAME, ATTR_WATERING_REQUIRED
from . import FloraPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flora Planner binary sensor."""
    coordinator: FloraPlannerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities(
        [FloraPlannerWateringSensor(coordinator, config_entry)],
        update_before_add=True,
    )


class FloraPlannerWateringSensor(CoordinatorEntity, BinarySensorEntity):
    """Represents a binary sensor that indicates if watering is required for a zone."""

    def __init__(self, coordinator: FloraPlannerCoordinator, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_name = config_entry.data[CONF_ZONE_NAME]
        self._attr_name = f"Flora Planner {self._zone_name} Watering Required"
        self._attr_unique_id = f"{config_entry.entry_id}_watering_required"
        self._attr_device_class = BinarySensorDeviceClass.MOISTURE

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if self.coordinator.data:
            return self.coordinator.data.get("watering_required", False)
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        if self.coordinator.data:
            return {
                "plant_watering_status": self.coordinator.data.get("plant_watering_status")
            }
        return {}
