# coding=utf-8
from __future__ import absolute_import

import subprocess
import threading

import octoprint.plugin
from octoprint.events import Events

try:
    import libregpio as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

NUM_RELAYS = 8


def default_relay(index):
    return dict(
        active=False,
        label="Relay {}".format(index),
        icon_on="\U0001F50C",   # 🔌
        icon_off="\u26AB",      # ⚫
        pin="",                 # e.g. "GPIOX_4"
        inverted=False,
        is_printer=False,
        autoconnect_delay=0,
        confirm_off=False,
        on_startup="skip",        # skip | on | off
        on_print_started="skip",  # skip | on | off
        on_print_stopped="skip",  # skip | on | off
        after_on_action="skip",   # skip | delay
        after_on_delay=0,
        after_on_target="off",    # on | off
        cmd_on="",
        cmd_off="",
    )


class PotatorelayPlugin(octoprint.plugin.StartupPlugin,
                               octoprint.plugin.ShutdownPlugin,
                               octoprint.plugin.SettingsPlugin,
                               octoprint.plugin.TemplatePlugin,
                               octoprint.plugin.AssetPlugin,
                               octoprint.plugin.EventHandlerPlugin,
                               octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self._gpio_outputs = {}   # pin name -> libregpio.OUT instance
        self._states = {}         # relay id "r1".."r8" -> bool (logical ON/OFF)
        self._timers = {}         # relay id -> threading.Timer
        self._lock = threading.RLock()

    # ---------------------------------------------------------------
    # SettingsPlugin
    # ---------------------------------------------------------------

    def get_settings_defaults(self):
        return dict(
            relays=[default_relay(i + 1) for i in range(NUM_RELAYS)]
        )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._init_gpio(reset=True)

    def get_settings_version(self):
        return 1

    # ---------------------------------------------------------------
    # Access permissions
    # ---------------------------------------------------------------

    def get_additional_permissions(self, *args, **kwargs):
        from octoprint.access.groups import ADMIN_GROUP, USER_GROUP
        return [
            dict(
                key="SWITCH",
                name="Relay switching",
                description="Allows switching relays on and off",
                roles=["admin", "user"],
                dangerous=True,
                default_groups=[ADMIN_GROUP, USER_GROUP],
            )
        ]

    # ---------------------------------------------------------------
    # StartupPlugin / ShutdownPlugin
    # ---------------------------------------------------------------

    def on_after_startup(self):
        if not GPIO_AVAILABLE:
            self._logger.warning(
                "libregpio is not installed - relay control is disabled. "
                "Install it with: pip install libregpio"
            )
        self._init_gpio(reset=False)
        self._apply_event("on_startup")

    def on_shutdown(self):
        for timer in self._timers.values():
            try:
                timer.cancel()
            except Exception:
                pass
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception:
                self._logger.exception("Error cleaning up GPIO on shutdown")

    # ---------------------------------------------------------------
    # GPIO handling
    # ---------------------------------------------------------------

    def _relays(self):
        return self._settings.get(["relays"], merged=True) or []

    def _relay_id(self, index):
        # index is 1-based
        return "r{}".format(index)

    def _init_gpio(self, reset=False):
        if not GPIO_AVAILABLE:
            return
        with self._lock:
            if reset:
                try:
                    GPIO.cleanup()
                except Exception:
                    self._logger.exception("Error during GPIO cleanup")
                self._gpio_outputs = {}

            for index, relay in enumerate(self._relays(), start=1):
                if not relay.get("active"):
                    continue
                pin = relay.get("pin")
                if not pin:
                    self._logger.warning(
                        "Relay %s is active but has no GPIO pin configured", index
                    )
                    continue
                try:
                    self._get_output(pin)
                except Exception:
                    self._logger.exception(
                        "Failed to initialize GPIO pin %s for relay %s", pin, index
                    )

    def _get_output(self, pin):
        if pin not in self._gpio_outputs:
            self._gpio_outputs[pin] = GPIO.OUT(pin)
        return self._gpio_outputs[pin]

    def _relay_by_id(self, relay_id):
        try:
            index = int(relay_id.lstrip("rR"))
        except (ValueError, AttributeError):
            return None, None
        relays = self._relays()
        if index < 1 or index > len(relays):
            return None, None
        return index, relays[index - 1]

    def get_status(self, relay_id):
        return self._states.get(relay_id, False)

    def set_relay(self, relay_id, target=None, run_side_effects=True):
        """target: True (on), False (off), or None (toggle)."""
        index, relay = self._relay_by_id(relay_id)
        if relay is None or not relay.get("active"):
            self._logger.warning("Attempted to set unknown/inactive relay %s", relay_id)
            return self.get_status(relay_id)

        current = self.get_status(relay_id)
        new_state = (not current) if target is None else bool(target)

        pin = relay.get("pin")
        if GPIO_AVAILABLE and pin:
            try:
                out = self._get_output(pin)
                physical_value = new_state
                if relay.get("inverted"):
                    physical_value = not physical_value
                out.output(1 if physical_value else 0)
            except Exception:
                self._logger.exception(
                    "Failed to drive GPIO pin %s for relay %s", pin, relay_id
                )

        self._states[relay_id] = new_state

        if run_side_effects:
            cmd = relay.get("cmd_on") if new_state else relay.get("cmd_off")
            if cmd:
                self._run_command(cmd, relay_id)

            if relay.get("is_printer"):
                self._handle_printer_relay(relay, new_state)

            # cancel any pending "after turned on" timer for this relay
            existing_timer = self._timers.pop(relay_id, None)
            if existing_timer:
                existing_timer.cancel()

            if new_state and relay.get("after_on_action") == "delay":
                delay = float(relay.get("after_on_delay") or 0)
                target_state = relay.get("after_on_target") == "on"
                if delay > 0:
                    timer = threading.Timer(
                        delay, self.set_relay, args=(relay_id, target_state)
                    )
                    timer.daemon = True
                    self._timers[relay_id] = timer
                    timer.start()

        self._plugin_manager.send_plugin_message(
            self._identifier,
            dict(type="status", id=relay_id, status=new_state),
        )
        return new_state

    def _run_command(self, cmd, relay_id):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception:
            self._logger.exception(
                "Failed to run side-effect command for relay %s", relay_id
            )

    def _handle_printer_relay(self, relay, new_state):
        if new_state:
            delay = float(relay.get("autoconnect_delay") or 0)

            def _connect():
                try:
                    self._printer.connect()
                except Exception:
                    self._logger.exception("Failed to auto-connect printer")

            if delay > 0:
                t = threading.Timer(delay, _connect)
                t.daemon = True
                t.start()
            else:
                _connect()
        else:
            try:
                self._printer.disconnect()
            except Exception:
                self._logger.exception("Failed to disconnect printer")

    def _apply_event(self, event_key):
        for index, relay in enumerate(self._relays(), start=1):
            if not relay.get("active"):
                continue
            action = relay.get(event_key, "skip")
            if action == "on":
                self.set_relay(self._relay_id(index), True)
            elif action == "off":
                self.set_relay(self._relay_id(index), False)

    # ---------------------------------------------------------------
    # EventHandlerPlugin
    # ---------------------------------------------------------------

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self._apply_event("on_print_started")
        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self._apply_event("on_print_stopped")

    # ---------------------------------------------------------------
    # TemplatePlugin
    # ---------------------------------------------------------------

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=True),
            dict(type="settings", custom_bindings=False),
        ]

    # ---------------------------------------------------------------
    # AssetPlugin
    # ---------------------------------------------------------------

    def get_assets(self):
        return dict(
            js=["js/potatorelay.js"],
            css=["css/potatorelay.css"],
        )

    # ---------------------------------------------------------------
    # SimpleApiPlugin
    # ---------------------------------------------------------------

    def get_api_commands(self):
        return dict(
            update=["subject"],
            getStatus=["subject"],
            listAllStatus=[],
        )

    def on_api_command(self, command, data):
        import flask

        if command == "listAllStatus":
            result = []
            for index, relay in enumerate(self._relays(), start=1):
                if not relay.get("active"):
                    continue
                rid = self._relay_id(index)
                result.append(dict(
                    id=rid,
                    name=relay.get("label", rid),
                    status=self.get_status(rid),
                ))
            return flask.jsonify(result)

        subject = data.get("subject")
        if not subject:
            return flask.make_response("Missing 'subject'", 400)

        index, relay = self._relay_by_id(subject)
        if relay is None:
            return flask.make_response("Unknown relay '{}'".format(subject), 404)

        if command == "getStatus":
            return flask.jsonify(dict(status=self.get_status(subject)))

        if command == "update":
            target = data.get("target", None)
            new_status = self.set_relay(subject, target)
            return flask.jsonify(dict(status=new_status))

        return flask.make_response("Unknown command", 400)

    # ---------------------------------------------------------------
    # GCODE @-command handling:  @OCTORELAY r1 [ON|OFF]
    # ---------------------------------------------------------------

    def process_at_command(self, comm_instance, phase, command, parameters, tags=None, *args, **kwargs):
        if command != "OCTORELAY":
            return

        parts = parameters.split()
        if not parts:
            self._logger.warning("Received @OCTORELAY without a relay id")
            return

        subject = parts[0].lower()
        target = None
        if len(parts) > 1:
            word = parts[1].upper()
            if word == "ON":
                target = True
            elif word == "OFF":
                target = False

        index, relay = self._relay_by_id(subject)
        if relay is None:
            self._logger.warning("@OCTORELAY referenced unknown relay '%s'", subject)
            return

        self.set_relay(subject, target)

    # ---------------------------------------------------------------
    # Software update hook
    # ---------------------------------------------------------------

    def get_update_information(self):
        return dict(
            potatorelay=dict(
                displayName="Le Potato Relay",
                displayVersion=self._plugin_version,
                type="github_release",
                current=self._plugin_version,
                pip="https://github.com/syntaxerror019/octoprint-potatorelay/archive/{target_version}.zip",
            )
        )


__plugin_name__ = "Le Potato Relay"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PotatorelayPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.atcommand.queuing":
            __plugin_implementation__.process_at_command,
        "octoprint.plugin.softwareupdate.check_config":
            __plugin_implementation__.get_update_information,
        "octoprint.access.permissions":
            __plugin_implementation__.get_additional_permissions,
    }
