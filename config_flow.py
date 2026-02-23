"""Config flow for Flora Planner."""
import logging
import random
import json
from datetime import date
from typing import Any, Dict

import voluptuous as vol
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    EntitySelector, EntitySelectorConfig, BooleanSelector
)
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN, CONF_ZONE_NAME, CONF_WEATHER_ENTITY, CONF_PLANTS,
    CONF_PLANT_NAME, CONF_WATER_INTERVAL, CONF_FEED_INTERVAL,
    CONF_PRUNE_MONTH, CONF_ANCHOR_DATE, CONF_USE_AI,
    CONF_SOIL_MOISTURE_ENTITY, CONF_GEMINI_API_KEY
)

_LOGGER = logging.getLogger(__name__)

MONTHS = {str(i): f"{i}" for i in range(1, 13)}

async def validate_api_key(api_key: str) -> bool:
    """Validate the Gemini API key."""
    try:
        genai.configure(api_key=api_key)
        # The model listing is a lightweight way to check auth
        await genai.GenerativeModel.list_models()
        return True
    except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated):
        return False
    except Exception:
        # Catch other potential issues like network errors
        return False

class FloraPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Flora Planner."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step to set up API Key."""
        errors = {}
        if user_input is not None:
            # Re-validate here in case user changes it
            if await self.hass.async_add_executor_job(validate_api_key, user_input[CONF_GEMINI_API_KEY]):
                self.hass.data[DOMAIN] = {"api_key": user_input[CONF_GEMINI_API_KEY]}
                return await self.async_step_zone()
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_GEMINI_API_KEY): str}),
            errors=errors
        )

    async def async_step_zone(self, user_input=None):
        """Handle the zone creation step."""
        if user_input is not None:
            # Combine API key from previous step with zone data
            data = {**self.hass.data[DOMAIN], **user_input}
            return self.async_create_entry(title=user_input[CONF_ZONE_NAME], data=data, options={CONF_PLANTS: []})

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema({
                vol.Required(CONF_ZONE_NAME): str,
                vol.Required(CONF_WEATHER_ENTITY): EntitySelector(EntitySelectorConfig(domain="weather")),
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Flora Planner to add/edit plants."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry
        self.current_plants = self.config_entry.options.get(CONF_PLANTS, [])
        self.plant_data = {}

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["add_plant_start", "remove_plant"])

    async def async_step_add_plant_start(self, user_input=None):
        """Start of the add plant flow: ask for name and if AI should be used."""
        errors = {}
        if user_input is not None:
            name = user_input[CONF_PLANT_NAME]
            if any(p[CONF_PLANT_NAME] == name for p in self.current_plants):
                errors["base"] = "name_exists"
            else:
                self.plant_data = user_input
                return await self.async_step_add_plant_details()

        return self.async_show_form(
            step_id="add_plant_start",
            data_schema=vol.Schema({
                vol.Required(CONF_PLANT_NAME): str,
                vol.Required(CONF_USE_AI, default=False): BooleanSelector(),
            }),
            errors=errors
        )

    async def async_step_add_plant_details(self, user_input=None):
        """Second step of adding a plant: show details form."""
        errors = {}
        if user_input is not None:
            # User has submitted the details form
            self.plant_data.update(user_input)
            self.plant_data[CONF_ANCHOR_DATE] = date.today().isoformat()
            self.current_plants.append(self.plant_data)
            return self.async_create_entry(title="", data={CONF_PLANTS: self.current_plants})

        # This is the first time we show the details form
        plant_name = self.plant_data.get(CONF_PLANT_NAME)
        use_ai = self.plant_data.get(CONF_USE_AI)
        
        ai_suggestions = {}
        if use_ai:
            try:
                ai_suggestions = await self._get_ai_suggestions(plant_name)
            except Exception as e:
                _LOGGER.error(f"Failed to get AI suggestions: {e}")
                errors["base"] = "ai_failure"

        plant_schema = vol.Schema({
            vol.Required(CONF_WATER_INTERVAL, default=ai_suggestions.get("water", 7)): cv.positive_int,
            vol.Required(CONF_FEED_INTERVAL, default=ai_suggestions.get("feed", 30)): cv.positive_int,
            vol.Required(CONF_PRUNE_MONTH, default=ai_suggestions.get("prune", "6")): SelectSelector(
                SelectSelectorConfig(options=list(MONTHS.keys()), mode=SelectSelectorMode.DROPDOWN, translation_key="pruning_months")
            ),
            vol.Optional(CONF_SOIL_MOISTURE_ENTITY): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="moisture")
            ),
        })

        return self.async_show_form(
            step_id="add_plant_details",
            data_schema=plant_schema,
            description_placeholders={"plant_name": plant_name},
            errors=errors
        )

    async def _get_ai_suggestions(self, plant_name: str) -> Dict[str, Any]:
        """Get plant care suggestions from Gemini."""
        prompt = (
            f"Voor de plant '{plant_name}', geef een JSON-object met 'watering_interval' in dagen, "
            f"'feeding_interval' in dagen, en 'pruning_month' als een nummer (1-12). "
            f"Geef alleen de JSON terug."
        )
        api_key = self.config_entry.data.get(CONF_GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        def _generate():
            genai.configure(api_key=api_key)
            return model.generate_content(prompt)

        response = await self.hass.async_to_executor(_generate)
        
        # Basic parsing, a real implementation needs more robust error handling
        text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        
        return {
            "water": data.get("watering_interval", 7),
            "feed": data.get("feeding_interval", 30),
            "prune": str(data.get("pruning_month", 6)),
        }

    async def async_step_remove_plant(self, user_input=None):
        """Handle removing a plant."""
        # This part is unchanged from the previous version
        if user_input is not None:
            plant_to_remove = user_input["plant_to_remove"]
            self.current_plants = [p for p in self.current_plants if p[CONF_PLANT_NAME] != plant_to_remove]
            return self.async_create_entry(title="", data={CONF_PLANTS: self.current_plants})

        plant_names = [p[CONF_PLANT_NAME] for p in self.current_plants]
        if not plant_names:
            return self.async_abort(reason="no_plants_to_remove")

        return self.async_show_form(
            step_id="remove_plant",
            data_schema=vol.Schema({vol.Required("plant_to_remove"): SelectSelector(SelectSelectorConfig(options=plant_names, mode=SelectSelectorMode.DROPDOWN))})
        )
