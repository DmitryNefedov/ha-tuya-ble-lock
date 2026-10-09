from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import REGIONS, TuyaApiError, TuyaAuthError, TuyaConnectionError, TuyaLockApi
from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_REGION, DEFAULT_REGION, DOMAIN


class TuyaBleLockConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CLIENT_ID])
            self._abort_if_unique_id_configured()
            api = TuyaLockApi(
                async_get_clientsession(self.hass),
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
                user_input[CONF_REGION],
            )
            try:
                await api.authenticate()
            except TuyaAuthError:
                errors["base"] = "invalid_auth"
            except TuyaConnectionError:
                errors["base"] = "cannot_connect"
            except TuyaApiError as err:
                errors["base"] = "tuya_error"
                placeholders["error"] = str(err)
            else:
                return self.async_create_entry(
                    title="Tuya BLE Lock (Cloud)", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                    vol.Required(CONF_REGION, default=DEFAULT_REGION): SelectSelector(
                        SelectSelectorConfig(
                            options=list(REGIONS), translation_key=CONF_REGION
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

