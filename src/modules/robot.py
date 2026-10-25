"""Robot -- the body Pip lives in: the OLED (real, emulated, or none), the eye engine, the tools,
and the background feeds that keep the face alive. `Robot()` boots all of it and starts animating;
`shutdown()` puts Pip to sleep and closes the board link. Modes (MCP, chat, demo) just drive it.
"""
from __future__ import annotations

import os
import sys
import time

from modules.assistant.tools import build_tools
from modules.espbridge import gps
from modules.espbridge.display import NullDisplay, WindowDisplay, connect_display
from faces import EyeEngine
from faces.actions import ping_pong
from faces.vibes import solarflare
from faces.widgets import battery_gauge, weather


class Robot:
    def __init__(self, *, emulate=False):
        self.bridge_mgr = None                   # set only when a real board answers
        self.oled = WindowDisplay() if emulate else self._connect_board()
        self.eyes = EyeEngine(self.oled.show, width=self.oled.width, height=self.oled.height,
                              fps=int(os.getenv("ROBOT_FPS", "24")),
                              set_brightness=self.oled.contrast,
                              bright=int(os.getenv("ROBOT_BRIGHTNESS", "255")))
        self.tools = build_tools(self.eyes, self.bridge_mgr)
        self.eyes.start()
        self._start_feeds()

    def _connect_board(self):
        """The real OLED over BLE, or a headless stub when there's no board (face-only)."""
        try:
            self.bridge_mgr, oled = connect_display()
            return oled
        except Exception as e:
            print(f"[robot] no display ({e}); running face-only", file=sys.stderr, flush=True)   # stdout = MCP stream
            return NullDisplay()

    def _start_feeds(self):
        """Real-world data wired to looping effects. Daemon threads / one-shot binds; nothing blocks."""
        weather.bind(gps.locate)                 # weather uses the host's real location, IP as fallback
        solarflare.watch(lambda: self.eyes.set_activity("solarflare"))   # yesterday's real M+ flares, replayed today
        if self.bridge_mgr is None:              # the rest read the physical board -> only with a link
            return
        bridge = self.bridge_mgr.bridge          # live link each call, so feeds survive a BLE reconnect
        ping_pong.bind(lambda: bridge().ping())  # real RTT off the live link
        pin = int(os.getenv("PIP_BATTERY_PIN", "34"))            # GPIO34: ADC1, input-only
        chg_pin = os.getenv("PIP_CHARGE_PIN")                    # e.g. TP4056 CHRG pin; unset = unknown

        def read_mv():
            b = bridge()
            b.adc.config(pin, atten=11)                         # ~3.3V range; idempotent, survives reconnect
            return b.adc.read_mv(pin)

        def charging():
            b = bridge()
            b.gpio.mode(int(chg_pin), "input_pullup")           # CHRG is open-drain: pulled low while charging
            return not b.gpio.read(int(chg_pin))

        battery_gauge.bind(read_mv, charging if chg_pin else None)

    def shutdown(self):
        """Sleepy face, stop animating, blank the panel, close the board link."""
        self.eyes.set_mood("sleepy")
        time.sleep(0.4)
        self.eyes.stop()
        try:
            self.oled.clear()
        except Exception:
            pass
        if self.bridge_mgr is not None:
            self.bridge_mgr.shutdown()
