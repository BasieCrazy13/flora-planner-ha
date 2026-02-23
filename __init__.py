"""The Flora Planner integration."""
import asyncio
import logging
from datetime import timedelta, datetime, date
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_WEATHER_ENTITY,
    CONF_ZONE_NAME,
    CONF_PLANTS,
    CONF_SOIL_MOISTURE_ENTITY,
    SOIL_MOISTURE_THRESHOLD,
    PRECIP_THRESHOLD,
    TEMP_THRESHOLD,
    CONF_GEMINI_API_KEY,
    ATTR_WEEKLY_STORY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Flora Planner from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    api_key = entry.data.get(CONF_GEMINI_API_KEY)

    if not api_key:
        _LOGGER.error("Gemini API key is not configured.")
        return False

    coordinator = FloraPlannerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class FloraPlannerCoordinator(DataUpdateCoordinator):
    """Data update coordinator for the Flora Planner integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        self.zone_name = self.config_entry.data[CONF_ZONE_NAME]
        self.weather_entity = self.config_entry.data[CONF_WEATHER_ENTITY]
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.zone_name}",
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self):
        """Fetch data and calculate needs."""
        weather_state = self.hass.states.get(self.weather_entity)
        if weather_state is None:
            raise UpdateFailed(f"Weather entity {self.weather_entity} not found")

        # Haal temperatuur en regen op uit de weer-entiteit
        temp = weather_state.attributes.get("temperature")
        # Let op: bij sommige weer-entiteiten heet dit anders, pas eventueel aan naar jouw specifieke sensor
        precip = weather_state.attributes.get("precipitation", 0) 

        try:
            zone_data = {
                "watering_required": False,
                "plant_watering_status": {},
                ATTR_WEEKLY_STORY: "Nog geen verhaal voor deze week."
            }
            plants = self.config_entry.options.get(CONF_PLANTS, [])
            today = date.today()

            # Variabele om bij te houden of we de configuratie moeten opslaan
            config_changed = False
            new_options = dict(self.config_entry.options)
            plants_copy = list(new_options.get(CONF_PLANTS, []))

            for i, plant in enumerate(plants):
                plant_name = plant["plant_name"]
                is_due = False

                # --- 1. Bodemsensor Override (De nieuwe AI code) ---
                soil_entity = plant.get(CONF_SOIL_MOISTURE_ENTITY)
                if soil_entity:
                    soil_state = self.hass.states.get(soil_entity)
                    if soil_state and soil_state.state not in ["unknown", "unavailable"]:
                        try:
                            moisture_level = float(soil_state.state)
                            if moisture_level < SOIL_MOISTURE_THRESHOLD:
                                is_due = True
                                _LOGGER.debug(f"Bodemvocht voor {plant_name} is laag ({moisture_level}%), sproeien vereist.")
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Kon bodemsensor '{soil_state.state}' niet lezen voor {soil_entity}")

                # --- 2. Kalender & Weer Logica (Alleen als bodemsensor niet al 'True' was) ---
                if not is_due:
                    base_interval = plant["watering_interval"]
                    anchor_date_obj = date.fromisoformat(plant["anchor_date"])
                    dynamic_interval = base_interval

                    # Heter dan de drempelwaarde? Interval korter maken!
                    if temp is not None and temp > TEMP_THRESHOLD:
                        dynamic_interval = max(1, base_interval - 1)

                    days_since_anchor = (today - anchor_date_obj).days
                    is_due = (days_since_anchor % dynamic_interval) == 0 and days_since_anchor >= 0

                    # --- ONZE REGEN FIX ---
                    if precip is not None and precip > PRECIP_THRESHOLD:
                        is_due = False # De natuur heeft gesproeid!
                        
                        # Reset de datum naar vandaag zodat hij morgen weer op dag 1 begint
                        if anchor_date_obj != today:
                            p_copy = dict(plants_copy[i])
                            p_copy["anchor_date"] = today.isoformat()
                            plants_copy[i] = p_copy
                            config_changed = True

                # --- 3. Resultaat verwerken ---
                if is_due:
                    zone_data["watering_required"] = True
                
                zone_data["plant_watering_status"][plant_name] = is_due
            
            # Sla de nieuwe datums op in de database als het geregend heeft
            if config_changed:
                new_options[CONF_PLANTS] = plants_copy
                self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

            # --- 4. Wekelijkse Verhaal Generatie (De nieuwe AI code) ---
            weekly_tasks = await self._calculate_weekly_tasks(plants)
            if weekly_tasks:
                story = await self._generate_story(weekly_tasks)
                zone_data[ATTR_WEEKLY_STORY] = story

            return zone_data

        except Exception as err:
            raise UpdateFailed(f"Error processing data: {err}") from err

    async def _calculate_weekly_tasks(self, plants: list) -> list[str]:
        """Calculate all tasks for the next 7 days."""
        tasks = set()
        today = date.today()
        language = self.hass.config.language
        
        for i in range(7):
            current_date = today + timedelta(days=i)
            
            for plant in plants:
                plant_name = plant["plant_name"]
                anchor = date.fromisoformat(plant["anchor_date"])
                days_since_anchor = (current_date - anchor).days

                if days_since_anchor < 0:
                    continue

                if days_since_anchor % plant["watering_interval"] == 0:
                    if language == "nl":
                        tasks.add(f"geef {plant_name} water")
                    else:
                        tasks.add(f"water {plant_name}")
                
                if days_since_anchor % plant["feeding_interval"] == 0:
                    if language == "nl":
                        tasks.add(f"geef {plant_name} voeding")
                    else:
                        tasks.add(f"feed {plant_name}")

                prune_month = int(plant["pruning_month"])
                if current_date.month == prune_month and current_date.day == 1:
                    if language == "nl":
                        tasks.add(f"snoei {plant_name}")
                    else:
                        tasks.add(f"prune {plant_name}")
        
        return list(tasks)

    async def _generate_story(self, tasks: list[str]) -> str:
        """Generate a weekly story using Gemini."""
        language = self.hass.config.language

        if not tasks:
            if language == "nl":
                return "Het is een rustige week in de tuin. Geniet van de stilte!"
            return "It is a quiet week in the garden. Enjoy the silence!"

        task_list = ", ".join(tasks)
        if language == "nl":
            prompt = (
                f"Schrijf een heel kort, leuk en motiverend tuinverhaal van 2 zinnen in het Nederlands "
                f"voor de komende week. De taken zijn: {task_list}. Begin de eerste zin met iets als "
                f"'Tijd om de handen uit de mouwen te steken!' of 'Deze week komt de tuin tot leven!'."
            )
        else:
            prompt = (
                f"Write a very short, fun, and motivating garden story of 2 sentences in English "
                f"for the coming week. The tasks are: {task_list}. Start the first sentence with something like "
                f"'Time to roll up your sleeves!' or 'The garden is coming to life this week!'."
            )
            
        api_key = self.config_entry.data[CONF_GEMINI_API_KEY]
        if not api_key:
            _LOGGER.error("Geen API key gevonden voor verhaal generatie.")
            return "Controleer je API key configuratie."

        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip().replace('\n', ' ')
                else:
                    _LOGGER.error(f"Gemini API error: {response.status}")
                    raise Exception(f"API returned {response.status}")
        except Exception as e:
            _LOGGER.warning(f"Could not generate weekly story with Gemini: {e}")
            if language == "nl":
                return "Deze week staan er klusjes op de planning! Kijk op de kalender wat er moet gebeuren."
            return "There are chores scheduled for this week! Check the calendar to see what needs to be done."