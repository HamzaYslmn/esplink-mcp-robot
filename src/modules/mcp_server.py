"""MCP server: exposes the robot's tools to Claude Code over stdio.

Claude Code spawns this process itself (`.mcp.json` is `{type: stdio, command: uv …}`)
and owns its lifecycle, talking JSON-RPC over stdin/stdout. Nothing else may write to
stdout or it corrupts the protocol -- our logs go to stderr.

With a board attached, esplink's own generated peripheral tools (gpio, adc, pwm, i2c, …)
are mounted as `board_*` on Pip's one shared BLE link, so there's never a second link.
"""
from __future__ import annotations

from importlib.metadata import version

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

INSTRUCTIONS = """\
Pip is a desk robot: an ESP32 with a 128x64 OLED showing animated eyes. It mirrors
how the coding session feels.

- face(name, gesture): the one visual entry point. A mood is held, a loop
  (activity/vibe/widget) runs until changed, the optional gesture plays once on top.
  name='idle' clears, name='vibe' plays a random vibe.
- notify(reason): pull the human's eyes to the desk when they're needed.
- board_* (only with a board attached): the ESP32's peripherals over Pip's own link.
  Pins are GPIO numbers; set board_gpio_mode before read/write; bytes are hex strings.
  Call board_status before acting. The OLED owns I2C bus 0
  (board_status shows its pins): don't deinit or re-pin it, and avoid board_system_reset /
  radio_off / deep_sleep -- they drop Pip's Bluetooth link.
"""

# Face tools only touch Pip's own screen: safe, repeatable, closed-world.
_SCREEN = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                          idempotentHint=True, openWorldHint=False)
_TITLES = {"face": "Set Pip's face", "notify": "Get the human's attention"}


def serve(robot, name="esplink-buddy"):
    """Run the FastMCP server over stdio so Claude Code can drive Pip (and its board)."""
    mcp = FastMCP(name, instructions=INSTRUCTIONS, version=version("esplink-buddy"),
                  website_url="https://github.com/HamzaYslmn/esplink-mcp-robot")
    for fn in robot.tools:
        if fn.__name__ in _TITLES:              # pin shortcuts are the Ollama brain's; MCP gets board_*
            mcp.tool(fn, annotations=_SCREEN.model_copy(update={"title": _TITLES[fn.__name__]}))
    if robot.bridge_mgr is not None:
        from esplink.mcp.tools import register_all
        board = FastMCP("board")
        register_all(board, robot.bridge_mgr)   # peripherals only -- no bridge_connect to steal the link
        mcp.mount(board, namespace="board", tool_names={"board_status": "status"})   # not board_board_status
    mcp.run(transport="stdio", show_banner=False)
