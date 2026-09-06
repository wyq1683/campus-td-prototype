#!/usr/bin/env bash
# Blender MCP Server launcher (stdio)
# Real repo path: d:\d\d\AI\Tools\blender_mcp  (mcp package inside /mcp)
# cd into the mcp package dir so `import blmcp` resolves (sandbox path-mapping workaround).
cd "D:/d/AI/Tools/blender_mcp/mcp" 2>/dev/null || cd "/d/d/AI/Tools/blender_mcp/mcp" 2>/dev/null
export PYTHONPATH="$PWD:${PYTHONPATH}"
export BLENDER_PATH="D:/建模/blender/blender.exe"
export BLENDER_MCP_HOST="localhost"
export BLENDER_MCP_PORT="9876"
exec "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -m blmcp --transport stdio "$@"
