"""One-off: name the ESP32 "pip" and pin its MAC in .env for fast BLE connect.

    uv run src/modules/espbridge/setup_board.py
"""
from __future__ import annotations

from pathlib import Path

import esplink

ENV = Path(__file__).parents[2] / ".env"  # src/.env (where main.py reads it)


def _set_env(key, value):
    lines = ENV.read_text().splitlines() if ENV.exists() else []
    kept = [ln for ln in lines if ln.split("=", 1)[0].strip() != key]
    kept.append(f"{key}={value}")
    ENV.write_text("\n".join(kept) + "\n")


def main():
    with esplink.connect(ble=True) as esp:
        esp.set_name("pip")
        mac = esp.info.mac
        print(f"named board 'pip', MAC = {mac}")
        _set_env("ROBOT_BLE_TARGET", mac)
        print(f"wrote ROBOT_BLE_TARGET={mac} to {ENV}")


if __name__ == "__main__":
    main()
