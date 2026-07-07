# IDA-MCP

IDA-MCP is an IDA Pro plugin that exposes IDA analysis, database modification,
debugger, and lifecycle operations through MCP. Each IDA instance runs a local
FastMCP HTTP server, and a standalone gateway provides a stable
multi-instance MCP endpoint.

## Layout

```text
IDA-MCP/
├── ida_mcp.py          # IDA plugin entry point, exposes PLUGIN_ENTRY()
├── ida-plugin.json     # IDA plugin metadata
├── ida_mcp/            # plugin package, gateway, proxy, tools, resources
├── install.py          # interactive installer
├── test/               # live-IDA pytest suite
├── API.md              # MCP, tool, resource, and internal HTTP contract
├── project.md          # repository map and boundaries
├── roadmap.md          # current direction and milestones
└── requirements.txt    # IDA Python runtime dependencies
```

## Runtime Model

- IDA loads `ida_mcp.py`, which starts `ida_mcp/plugin_runtime.py`.
- Each IDA instance chooses a free port starting at `ida_default_port` and serves MCP at `/mcp/`.
- The standalone gateway listens on `127.0.0.1:11338`, registers instances under `/internal/*`, and exposes the proxy MCP endpoint at `/mcp`.
- Tool registration is decorator based: use `@tool` plus `@idaread` or `@idawrite`.
- Gateway requests require `gateway_token`; an empty token fails closed.
- `py_eval`, `patch_bytes`, `apply_patch`, and `dbg_*` tools are unsafe and gated by `enable_unsafe=false` by default in `ida_mcp/config.conf`.

## Installation

Requirements:

- Python > 3.11

Run the interactive installer from the repository root:

```bash
python install.py
```

The installer performs the full setup flow:

1. Locate the IDA installation directory.
2. Locate the IDAPython interpreter used by that IDA installation.
3. Optionally install `requirements.txt` into IDA's Python environment.
4. Copy `ida_mcp.py`, `ida-plugin.json`, and the `ida_mcp/` package into IDA's `plugins/` directory.
5. Review and write `ida_mcp/config.conf`, including an auto-generated gateway token.

For manual installation, copy `ida_mcp.py`, `ida-plugin.json`, and the
`ida_mcp/` directory into IDA's plugin directory, then install dependencies into
IDA's Python environment:

```bash
<ida_python> -m pip install -r requirements.txt
```

Open a database in IDA and wait for initial analysis. The plugin starts its
per-instance MCP server automatically when HTTP transport is enabled.

## Gateway And CLI

```bash
# Start the standalone gateway
python ida_mcp/command.py gateway start --json

# Status, stop, open IDA, call a tool directly
python ida_mcp/command.py gateway status
python ida_mcp/command.py gateway stop
python ida_mcp/command.py ida open ./target.exe
python ida_mcp/command.py tool call get_metadata --port 10000
```

Default endpoints:

- Gateway MCP proxy: `http://127.0.0.1:11338/mcp`
- Gateway internal API: `http://127.0.0.1:11338/internal/*`
- Direct IDA instance MCP: `http://127.0.0.1:<instance_port>/mcp/`

## Tests

Tests require a running gateway and at least one registered IDA instance.

```bash
python test/test.py
python test/test.py --core --analysis
python test/test.py --transport=http --analysis

pytest -m "core or analysis"
pytest -m "not debug"
pytest --transport=http
```

The `debug` marker is excluded by default because it requires an active
debugger. API call logs are written to `.artifacts/api_logs/`.

## Documentation

- `API.md` documents the MCP tools, resources, proxy behavior, and internal HTTP routes.
- `project.md` explains repository responsibilities and module boundaries.
- `roadmap.md` tracks current stabilization work.
