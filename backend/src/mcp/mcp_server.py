"""JSON-RPC 2.0 Model Context Protocol (MCP) Server for Bitget OctaCore."""

import json
import sys
from typing import Any, Dict
from src.core.llm_client import TOOL_MAP, OPENAI_TOOL_SPECS


def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process incoming JSON-RPC 2.0 MCP request."""
    method = request.get("method")
    req_id = request.get("id")

    if method == "tools/list":
        # Convert OpenAI tool specs into MCP tools format
        mcp_tools = []
        for spec in OPENAI_TOOL_SPECS:
            fn = spec.get("function", {})
            mcp_tools.append({
                "name": fn.get("name"),
                "description": fn.get("description"),
                "inputSchema": fn.get("parameters", {"type": "object", "properties": {}})
            })
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": mcp_tools}
        }

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name not in TOOL_MAP:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found."}
            }

        try:
            fn = TOOL_MAP[tool_name]
            res = fn(**args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)}
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not recognized."}
    }


def run_mcp_stdio():
    """Run MCP server over standard input/output for desktop AI tools (Claude Desktop, Cursor, Codex)."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            res = handle_mcp_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_mcp_stdio()
