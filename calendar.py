"""Calendar platform for Flora Planner."""
from datetime import date, timedelta, datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_ZONE_NAME,
    CONF_PLANTS,
    CONF_PRUNE_MONTH,
    CONF_SOW_MONTH,
    CONF_HARVEST_MONTH,
    EVENT_WATER,
    EVENT_FEED,
    EVENT_PRUNE,
    EVENT_SOW,
    EVENT_HARVEST,
)
from . import FloraPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flora Planner calendar platform."""
    coordinator: FloraPlannerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [FloraPlannerCalendar(coordinator, config_entry)], update_before_add=True
    )


class FloraPlannerCalendar(CoordinatorEntity, CalendarEntity):
    """A calendar entity for the Flora Planner integration."""

    def __init__(self, coordinator: FloraPlannerCoordinator, config_entry: ConfigEntry):
        """Initialize the Flora Planner calendar."""
        super().__init__(coordinator)
        self._zone_name = config_entry.data[CONF_ZONE_NAME]
        self._attr_name = f"Flora Planner {self._zone_name}"
        self._attr_unique_id = f"{config_entry.entry_id}_calendar"
        self._attr_icon = "mdi:flower"
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        events = []
        plants = self.coordinator.config_entry.options.get(CONF_PLANTS, [])
        
        for plant in plants:
            plant_name = plant["plant_name"]
            anchor_date = date.fromisoformat(plant["anchor_date"])
            
            water_interval = plant["watering_interval"]
            feed_interval = plant["feeding_interval"]
            prune_month = int(plant[CONF_PRUNE_MONTH])
            sow_month = int(plant.get(CONF_SOW_MONTH, 0))
            harvest_month = int(plant.get(CONF_HARVEST_MONTH, 0))

            # Iterate through the date range to generate events
            current_date = start_date.date()
            while current_date <= end_date.date():
                days_since_anchor = (current_date - anchor_date).days
                if days_since_anchor < 0:
                    current_date += timedelta(days=1)
                    continue

                # Watering
                if (days_since_anchor % water_interval) == 0:
                    events.append(self._create_event(current_date, f"Water {plant_name}", EVENT_WATER))

                # Feeding
                if (days_since_anchor % feed_interval) == 0:
                    events.append(self._create_event(current_date, f"Feed {plant_name}", EVENT_FEED))

                # Pruning
                if current_date.month == prune_month and current_date.day == 1:
                     events.append(self._create_event(current_date, f"Prune {plant_name}", EVENT_PRUNE))

                # Sowing
                if sow_month > 0 and current_date.month == sow_month and current_date.day == 1:
                     events.append(self._create_event(current_date, f"Sow {plant_name}", EVENT_SOW))

                # Harvesting
                if harvest_month > 0 and current_date.month == harvest_month and current_date.day == 1:
                     events.append(self._create_event(current_date, f"Harvest {plant_name}", EVENT_HARVEST))

                current_date += timedelta(days=1)

        # Sort events and update the next upcoming event
        events.sort(key=lambda x: x.start)
        now = datetime.now()
        future_events = [e for e in events if e.start >= now.date() or (e.start_datetime_local and e.start_datetime_local >= now)]
        self._event = future_events[0] if future_events else None

        return events

    def _create_event(self, event_date: date, summary: str, event_type: str) -> CalendarEvent:
        """Helper to create a CalendarEvent."""
        return CalendarEvent(
            summary=summary,
            start=event_date,
            end=event_date,
            description=f"Task for zone: {self._zone_name}",
            uid=f"{self.unique_id}-{event_type}-{event_date.isoformat()}"
        )
