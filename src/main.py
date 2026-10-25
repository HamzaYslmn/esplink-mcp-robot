"""Run Pip from a checkout -- the same as the installed `esplink-buddy` command:

    uv run src/main.py              # MCP server (what Claude Code spawns via .mcp.json)
    uv run src/main.py demo -e      # play any face in the on-screen OLED emulator
    uv run src/main.py --help       # every mode and flag

Running this file puts src/ on sys.path; the logic lives in modules/cli.py."""
from modules.cli import main

if __name__ == "__main__":
    main()
