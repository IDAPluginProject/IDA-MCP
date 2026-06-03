# HTTP-Only Transport Removal Design

## Context

IDA-MCP currently exposes MCP capabilities through HTTP and still contains legacy stdio transport support. The project direction is to remove stdio entirely and keep HTTP as the only supported transport.

True stdio support is concentrated in the proxy entrypoint, transport configuration, plugin startup checks, registration gates, pytest transport selection, API logs, and documentation. References to `stdin`, `stdout`, and `stderr` used for subprocess I/O or `py_eval` output are not transport support and must remain where semantically correct.

## Goal

Remove stdio transport support completely:

- Delete the stdio proxy entrypoint.
- Remove stdio configuration and accessors.
- Make plugin and registry lifecycle depend only on HTTP transport.
- Make tests HTTP-only.
- Update documentation so HTTP is the only described MCP transport.

## Non-Goals

- Do not remove generic process I/O usage such as subprocess `stdin`, `stdout`, or `stderr` redirection.
- Do not remove `py_eval` result fields named `stdout` or `stderr`.
- Do not redesign the HTTP gateway, direct instance HTTP server, or tool/resource API contracts.
- Do not change unsafe tool gating.

## Recommended Approach

Use a focused removal with HTTP naming cleanup where needed. This avoids compatibility shims and prevents the architecture from appearing to support dual transports after stdio is gone.

## Architecture Changes

### Configuration Layer

`ida_mcp/config.conf` will remove `enable_stdio` and describe HTTP as the only MCP transport. `ida_mcp/config.py` will remove the `enable_stdio` default, module docstring entry, and `is_stdio_enabled()` accessor. `is_http_enabled()` remains as the single transport gate.

### Plugin Startup

`ida_mcp.py` will stop importing or checking `is_stdio_enabled()`. Startup validation will only check `is_http_enabled()`. Logging will report HTTP startup directly instead of listing multiple transport modes.

### Gateway And Registry

`ida_mcp/registry.py` will stop importing `is_stdio_enabled()`. Instance registration will be skipped only when HTTP is disabled. HTTP proxy lifecycle behavior remains unchanged.

### Proxy Layer

`ida_mcp/proxy/ida_mcp_proxy.py` will be deleted because it is the stdio transport entrypoint. `ida_mcp/proxy/_server.py` will keep the shared FastMCP proxy server used by the gateway HTTP endpoint, and its comments/docstrings will be updated to avoid stdio references.

### Tests

The pytest suite will become HTTP-only:

- Remove `stdio` and `both` from `--transport` choices; keep `--transport=http` as the only accepted explicit transport for existing HTTP test commands.
- Replace `call_tool_stdio` usage with HTTP calls.
- Remove stdio API log buckets and stdio log file generation.
- Update test runner help and defaults to HTTP-only.
- Keep resource tests parameterized only when still useful; otherwise treat transport as `http`.

### Documentation

Update project documentation to describe only HTTP:

- `README.md` examples use default HTTP behavior and may show `--transport=http` as an explicit HTTP-only test command.
- `API.md` continues to document gateway MCP proxy, direct IDA instance MCP, and internal HTTP routes.
- `project.md`, `ida_mcp/project.md`, and roadmaps remove stdio transport claims.

## Error Handling

When HTTP is disabled, plugin startup should fail clearly with a message that HTTP mode is disabled in `config.conf`. No stdio fallback or compatibility path will be offered.

## Testing Strategy

Run static and unit-level tests that do not require a live IDA instance first. Then run the HTTP live-IDA suite when a gateway and instance are available:

- `pytest test/test_lifecycle.py test/test_server_factory.py`
- `pytest --transport=http -m "not debug"`

If a live gateway or IDA instance is unavailable, report that limitation and include the exact command to run manually.

## Acceptance Criteria

- Searching source, tests, and docs finds no true stdio transport support.
- `ida_mcp/proxy/ida_mcp_proxy.py` no longer exists.
- Config has no `enable_stdio` setting.
- Tests default to HTTP-only behavior.
- Documentation presents HTTP as the only MCP transport.
- Incidental `stdout`/`stderr`/`stdin` references remain where they are not transport support.
