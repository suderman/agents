#!/usr/bin/env python3
"""Resolve declared MCP servers for this host: print the JSON a harness should receive.

A server with "optional": true is kept only when its stdio command is on PATH,
so machine-specific servers such as DaVinci Resolve stay off other hosts.
The flag is removed because harnesses validate their own server fields.
"""

import json
import shutil
import sys
from pathlib import Path


def servers(source):
    declared = json.loads(Path(source).read_text())
    if not isinstance(declared, dict) or not isinstance(declared.get("mcpServers", {}), dict):
        raise ValueError(f"MCP declarations must contain an mcpServers object: {source}")
    result = {}
    for name, server in declared.get("mcpServers", {}).items():
        if not isinstance(server, dict):
            raise ValueError(f"MCP server must be an object: {name}")
        server = dict(server)
        optional = server.pop("optional", False)
        if not isinstance(optional, bool) or optional and not isinstance(server.get("command"), str):
            raise ValueError(f"MCP server {name}: optional must be a boolean on a stdio server")
        if optional and not shutil.which(server["command"]):
            continue
        result[name] = server
    return {**declared, "mcpServers": result}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: mcp.py SOURCE")
    try:
        print(json.dumps(servers(sys.argv[1]), indent=2))
    except (OSError, ValueError) as error:
        sys.exit(f"mcp: {error}")
