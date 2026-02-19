"""
setup_claude.py — Auto-configure Claude Desktop to use the BirdEye MCP server.

Run this once, then restart Claude Desktop. That's it.

    python setup_claude.py

Works on Windows and Mac.
"""

import json
import os
import sys


def main():
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    python_exe = sys.executable

    # Find Claude Desktop config location
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ.get("APPDATA", ""), "Claude")
    elif sys.platform == "darwin":
        config_dir = os.path.expanduser("~/Library/Application Support/Claude")
    else:
        print("Claude Desktop is not available on Linux.")
        print("Add this to your MCP-compatible tool's config manually:")
        print()
        print(json.dumps({
            "mcpServers": {
                "birdeye-outreach": {
                    "command": python_exe,
                    "args": [server_path]
                }
            }
        }, indent=2))
        return

    config_file = os.path.join(config_dir, "claude_desktop_config.json")

    # Load existing config if it exists
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            print(f"Found existing Claude Desktop config at:\n  {config_file}")
        except (json.JSONDecodeError, IOError):
            print("Existing config file could not be read. Starting fresh.")
            config = {}
    else:
        print(f"No existing config found. Creating new one at:\n  {config_file}")

    # Add BirdEye server entry
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["birdeye-outreach"] = {
        "command": python_exe,
        "args": [server_path]
    }

    # Create the directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Write the updated config
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print()
    print("Done! BirdEye Outreach is now configured in Claude Desktop.")
    print()
    print(f"  Python:  {python_exe}")
    print(f"  Server:  {server_path}")
    print(f"  Config:  {config_file}")
    print()
    print("Next step: Restart Claude Desktop.")
    print("You'll see a hammer icon at the bottom of the chat window")
    print("showing the BirdEye tools are available.")
    print()


if __name__ == "__main__":
    main()
