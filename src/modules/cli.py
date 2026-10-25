"""esplink-buddy -- Pip, the ESP32 desk robot with animated OLED eyes.

  esplink-buddy             MCP server over stdio (Claude Code spawns this)
  esplink-buddy chat        talk to Pip through a local Ollama model
  esplink-buddy demo        menu: play any face live
  esplink-buddy gif zen     render a 30s GIF of one face (name or menu number; no board)

Add -e / --emulate to show the 128x64 OLED in a desktop window instead of the real board
over Bluetooth. Settings come from .env (see src/.env.example); every one has a default.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

# emoji-safe console on Windows (cp1254 etc.) for our own logging
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

_SRC = Path(__file__).resolve().parent.parent   # the repo's src/ when run from a checkout
load_dotenv(Path.cwd() / ".env")                # .env beside wherever you launched (uvx)
load_dotenv(_SRC / ".env")                       # repo's src/.env, if present
load_dotenv(_SRC / ".env.example")               # repo defaults; no-op once installed


def _parse(argv):
    p = argparse.ArgumentParser(prog="esplink-buddy", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", nargs="?", default="mcp", choices=("mcp", "chat", "demo", "gif"),
                   help="what to run (default: mcp)")
    p.add_argument("face", nargs="?", help="gif only: a face name or demo-menu number")
    p.add_argument("-e", "--emulate", "--no-display", action="store_true",
                   default=os.getenv("ROBOT_NO_DISPLAY", "").lower() in ("1", "true", "yes", "on"),
                   help="OLED in a desktop window, no board (env: ROBOT_NO_DISPLAY=true)")
    args = p.parse_args(argv)
    if (args.mode == "gif") != bool(args.face):
        p.error("a face goes with `gif` only, e.g. `esplink-buddy gif zen`")
    return args


def main(argv=None):
    args = _parse(argv)
    if args.mode == "gif":                         # pure render: no board, no window, no Robot
        from modules.demo import save_gif
        sys.exit(0 if save_gif(args.face) else 2)

    from modules.robot import Robot
    robot = Robot(emulate=args.emulate)            # boots the face (+ board link) and starts animating
    # Ctrl+C with the Tk emulator up: on Windows Tcl grabs the console (WindowDisplay re-traps it);
    # on Unix re-assert Python's handler so a terminal Ctrl+C still raises KeyboardInterrupt here.
    if args.emulate and sys.platform != "win32":
        signal.signal(signal.SIGINT, signal.default_int_handler)
    if args.mode == "demo":
        from modules.demo import demo as run
    elif args.mode == "chat":
        from modules.assistant.brain import chat as run
    else:
        from modules.mcp_server import serve as run   # MCP over stdio; Claude Code owns this process
    try:
        run(robot)
    except KeyboardInterrupt:
        pass
    finally:
        robot.shutdown()
        os._exit(0)        # the daemon Tk thread's live Tcl interpreter can hang a normal exit


if __name__ == "__main__":
    main()
