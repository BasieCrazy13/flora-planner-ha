"""Switch platform for Flora Planner Smart Watering."""
import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    ATTR_ENTITY_ID,
    STATE_ON,
)

from .const import (
    DOMAIN,
    CONF_ZONE_NAME,
    CONF_SPRINKLER_ENTITY,
    CONF_CYCLE_MINUTES,
    CONF_SOAK_MINUTES,
    CONF_MAX_CYCLES,
    CONF_PLANTS,
    CONF_SOIL_MOISTURE_ENTITY,
    CONF_MIN_MOISTURE,
    CONF_AUTO_WATER,
    SOIL_MOISTURE_THRESHOLD,
)
from . import FloraPlannerCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flora Planner switch platform."""
    coordinator: FloraPlannerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Alleen toevoegen als er een sproeier is geconfigureerd
    if config_entry.data.get(CONF_SPRINKLER_ENTITY):
        async_add_entities(
            [FloraPlannerSmartWateringSwitch(coordinator, config_entry)],
            update_before_add=True,
        )

class FloraPlannerSmartWateringSwitch(CoordinatorEntity, SwitchEntity):
    """Smart watering switch that cycles the sprinkler based on moisture."""

    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator: FloraPlannerCoordinator, config_entry: ConfigEntry):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._zone_name = config_entry.data[CONF_ZONE_NAME]
        self._sprinkler_entity = config_entry.data[CONF_SPRINKLER_ENTITY]
        self._cycle_minutes = config_entry.data.get(CONF_CYCLE_MINUTES, 5)
        self._soak_minutes = config_entry.data.get(CONF_SOAK_MINUTES, 10)
        self._max_cycles = config_entry.data.get(CONF_MAX_CYCLES, 5)
        
        self._attr_name = f"Flora Planner {self._zone_name} Smart Watering"
        self._attr_unique_id = f"{config_entry.entry_id}_smart_watering"
        self._is_active = False
        self._watering_task = None

    @property
    def is_on(self) -> bool:
        """Return true if the smart watering cycle is running."""
        return self._is_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the smart watering cycle."""
        if self._is_active:
            return
        
        self._is_active = True
        self.async_write_ha_state()
        
        # Start the background task
        self._watering_task = self.hass.async_create_task(self._run_watering_cycle())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the smart watering cycle."""
        self._is_active = False
        if self._watering_task:
            self._watering_task.cancel()
            self._watering_task = None
        
        # Ensure sprinkler is off when we stop
        await self._control_sprinkler(False)
        self.async_write_ha_state()

    async def _run_watering_cycle(self):
        """The logic loop for cycle & soak."""
        try:
            for cycle in range(1, self._max_cycles + 1):
                if not self._is_active:
                    break

                # 1. Check if water is needed
                if not self._check_if_water_needed():
                    _LOGGER.info(f"Smart Watering {self._zone_name}: Grond is vochtig genoeg. Stoppen.")
                    break

                _LOGGER.info(f"Smart Watering {self._zone_name}: Start cyclus {cycle}/{self._max_cycles}")

                # 2. Sproeien
                await self._control_sprinkler(True)
                # Wacht sproeitijd (in seconden)
                for _ in range(self._cycle_minutes * 60):
                    if not self._is_active: break
                    await asyncio.sleep(1)

                # 3. Stoppen en weken
                await self._control_sprinkler(False)
                
                if cycle < self._max_cycles and self._is_active:
                    _LOGGER.info(f"Smart Watering {self._zone_name}: Weken voor {self._soak_minutes} minuten.")
                    # Wacht weektijd (in seconden)
                    for _ in range(self._soak_minutes * 60):
                        if not self._is_active: 
                            break
                        await asyncio.sleep(1)

        except asyncio.CancelledError:
            _LOGGER.info(f"Smart Watering {self._zone_name}: Geannuleerd.")
        finally:
            self._is_active = False
            await self._control_sprinkler(False)
            self.async_write_ha_state()

    def _check_if_water_needed(self) -> bool:
        """Check soil sensors. Returns True if ANY plant is too dry."""
        plants = self.coordinator.config_entry.options.get(CONF_PLANTS, [])
        needs_water = False
        
        has_sensors = False
        for plant in plants:
            # Als plant niet op automatische sproeier zit, negeren we hem voor de switch
            if not plant.get(CONF_AUTO_WATER, True):
                continue

            sensor = plant.get(CONF_SOIL_MOISTURE_ENTITY)
            threshold = plant.get(CONF_MIN_MOISTURE, SOIL_MOISTURE_THRESHOLD)
            
            if sensor:
                has_sensors = True
                state = self.hass.states.get(sensor)
                if state and state.state not in ["unknown", "unavailable"]:
                    try:
                        val = float(state.state)
                        if val < threshold:
                            _LOGGER.debug(f"Plant {plant['plant_name']} is te droog ({val}% < {threshold}%).")
                            needs_water = True
                    except ValueError:
                        pass
        
        # Als er geen sensoren zijn, gaan we ervan uit dat we gewoon het programma moeten draaien
        if not has_sensors:
            return True
            
        return needs_water

    async def _control_sprinkler(self, turn_on: bool):
        """Turn the real sprinkler entity on or off."""
        service = SERVICE_TURN_ON if turn_on else SERVICE_TURN_OFF
        if self._sprinkler_entity:
             await self.hass.services.async_call(
                "homeassistant",
                service,
                {ATTR_ENTITY_ID: self._sprinkler_entity},
                blocking=True
            )