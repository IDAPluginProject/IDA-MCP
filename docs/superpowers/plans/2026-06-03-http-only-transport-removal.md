# HTTP-Only Transport Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove stdio transport support completely and keep HTTP as the only supported MCP transport.

**Architecture:** The HTTP gateway and direct IDA instance HTTP server remain unchanged. The work deletes the stdio proxy entrypoint, removes stdio configuration and lifecycle gates, makes the test harness HTTP-only, and updates documentation to describe only HTTP.

**Tech Stack:** Python, FastMCP, Starlette/Uvicorn gateway, pytest, Markdown documentation.

---

## File Structure

- Delete: `ida_mcp/proxy/ida_mcp_proxy.py` — legacy FastMCP stdio entrypoint.
- Modify: `ida_mcp/config.conf` — remove `enable_stdio` and dual-transport comments.
- Modify: `ida_mcp/config.py` — remove `enable_stdio` defaults/docs and `is_stdio_enabled()`.
- Modify: `ida_mcp.py` — make plugin startup validation and logging HTTP-only.
- Modify: `ida_mcp/registry.py` — gate instance registration only on HTTP.
- Modify: `ida_mcp/proxy/_server.py` — remove comments claiming stdio/HTTP shared transport.
- Modify: `test/conftest.py` — make pytest tool calls, transport option, logs, and cached fixtures HTTP-only.
- Modify: `test/test.py` — make the live test runner HTTP-only.
- Modify: `test/test_lifecycle.py` — update registry retry test to patch HTTP only.
- Modify: `README.md`, `project.md`, `API.md`, `roadmap.md`, `ida_mcp/project.md`, `ida_mcp/roadmap.md` — remove stdio support descriptions.

## Task 1: Remove stdio config and startup gates

**Files:**
- Modify: `ida_mcp/config.conf:3-9`
- Modify: `ida_mcp/config.py:5-10`, `ida_mcp/config.py:43-48`, `ida_mcp/config.py:334-348`
- Modify: `ida_mcp.py:113-120`, `ida_mcp.py:253-267`
- Modify: `ida_mcp/registry.py:19-31`, `ida_mcp/registry.py:402-426`, `ida_mcp/registry.py:462-465`
- Test: `test/test_lifecycle.py:1110-1128`

- [ ] **Step 1: Write failing assertions for HTTP-only config**

  Add or update lifecycle/config assertions in `test/test_lifecycle.py` so they verify `enable_stdio` is no longer a supported config key and `is_stdio_enabled` is not present:

  ```python
  def test_config_exposes_only_http_transport_switch(self):
      assert not hasattr(config, "is_stdio_enabled")
      fake_config = {"enable_http": True}
      with patch("ida_mcp.config.load_config", return_value=fake_config):
          assert config.is_http_enabled() is True
  ```

- [ ] **Step 2: Run the focused failing test**

  Run: `pytest test/test_lifecycle.py::TestRegistryStartup::test_config_exposes_only_http_transport_switch -v`

  Expected before implementation: FAIL because `ida_mcp.config.is_stdio_enabled` still exists or the test method is not yet in the expected class.

- [ ] **Step 3: Remove stdio from config files**

  In `ida_mcp/config.conf`, replace the transport section with:

  ```conf
  # HTTP 是唯一支持的 MCP 连接方式

  # ==================
  # 传输方式开关
  # ==================
  enable_http = true # 是否启用 HTTP 代理模式（供 MCP 客户端通过 URL 连接）
  enable_unsafe = true # 是否启用 unsafe 工具（py_eval、调试器相关工具）
  ```

  In `ida_mcp/config.py`, remove the docstring line for `enable_stdio`, remove `_DEFAULT_CONFIG["enable_stdio"]`, and delete:

  ```python
  def is_stdio_enabled() -> bool:
      """Whether stdio mode (coordinator) is enabled."""
      config = load_config()
      return bool(config.get("enable_stdio", False))
  ```

- [ ] **Step 4: Make plugin startup HTTP-only**

  In `ida_mcp.py`, remove `is_stdio_enabled` from the config import and replace the transport check in `IDAMCPPlugin.run()` with:

  ```python
  if not is_http_enabled():
      plugin_runtime._warn(
          "HTTP mode is disabled in config.conf. No MCP server started."
      )
      return
  plugin_runtime._info("HTTP transport enabled.")
  ```

- [ ] **Step 5: Make registry registration HTTP-only**

  In `ida_mcp/registry.py`, remove `is_stdio_enabled` from the import list and replace both registration guards with:

  ```python
  if not is_http_enabled():
      return False
  ```

  For `init_and_register()`, use:

  ```python
  if not is_http_enabled():
      return
  ```

- [ ] **Step 6: Update registry retry test**

  Replace the nested stdio/http patches in `test/test_lifecycle.py` with HTTP-only setup:

  ```python
  with patch("ida_mcp.registry.is_http_enabled", return_value=True):
      with patch("ida_mcp.registry.ensure_registry_server", return_value=True) as mock_ensure:
          with patch(
              "ida_mcp.registry._request_json",
              side_effect=[None, {"status": "ok"}],
          ) as mock_request:
              with patch("atexit.register"):
                  with patch.object(registry, "_deregister_registered", False):
                      registry.init_and_register(10000, "input.bin", "db.i64")
  ```

- [ ] **Step 7: Verify config/startup tests**

  Run: `pytest test/test_lifecycle.py -k "config_exposes_only_http_transport_switch or init_and_register_retries_remote_registration" -v`

  Expected: both selected tests PASS.

- [ ] **Step 8: Checkpoint without commit**

  Run: `git diff -- ida_mcp/config.conf ida_mcp/config.py ida_mcp.py ida_mcp/registry.py test/test_lifecycle.py`

  Expected: diff only removes stdio transport config/gates and updates the HTTP-only tests. Do not commit unless the user explicitly requests it.

## Task 2: Delete stdio proxy entrypoint and clean proxy comments

**Files:**
- Delete: `ida_mcp/proxy/ida_mcp_proxy.py`
- Modify: `ida_mcp/proxy/_server.py:1-7`
- Test: source grep validation

- [ ] **Step 1: Delete the stdio entrypoint**

  Remove `ida_mcp/proxy/ida_mcp_proxy.py` entirely.

- [ ] **Step 2: Update proxy server docstring**

  Replace `ida_mcp/proxy/_server.py:1-7` with:

  ```python
  """Gateway FastMCP proxy server instance.

  This module creates the FastMCP server used by the HTTP gateway proxy and
  registers all forwarded tools.
  """
  ```

- [ ] **Step 3: Verify proxy source has no true stdio references**

  Run: `rg -n "stdio|ida_mcp_proxy" ida_mcp/proxy ida_mcp.py ida_mcp/registry.py ida_mcp/config.py`

  Expected: no matches.

- [ ] **Step 4: Checkpoint without commit**

  Run: `git diff -- ida_mcp/proxy/_server.py ida_mcp/proxy/ida_mcp_proxy.py`

  Expected: deleted stdio entrypoint and updated HTTP-only proxy docstring. Do not commit unless the user explicitly requests it.

## Task 3: Convert pytest harness to HTTP-only

**Files:**
- Modify: `test/conftest.py:1-20`, `test/conftest.py:83-87`, `test/conftest.py:246-331`, `test/conftest.py:347-430`, `test/conftest.py:589-604`, `test/conftest.py:701-728`, `test/conftest.py:738-794`

- [ ] **Step 1: Capture current stdio option behavior**

  Run: `pytest --transport=stdio --collect-only`

  Expected before implementation: collection accepts the `stdio` option, then either collects tests or skips live-IDA dependent fixtures.

- [ ] **Step 2: Make `--transport` HTTP-only**

  In `test/conftest.py`, replace the option definition with:

  ```python
  parser.addoption(
      "--transport",
      action="store",
      default="http",
      choices=["http"],
      help="Transport mode to test: http (default: http)",
  )
  ```

  Update the module docstring so it says:

  ```python
  """pytest 配置和共享 fixtures。

  测试框架设计：
  1. gateway_internal_available - 检查 gateway 内部 API 是否运行
  2. instance_port - 获取可用 IDA 实例端口
  3. tool_caller - 通过 HTTP proxy 调用工具
  4. 前置信息 fixtures（session 级别缓存）
  5. API 调用日志 - 保存到 .artifacts/api_logs/ 目录，文件名为 http_*.json

  运行方式：
      pytest
      pytest --transport=http
  """
  ```

- [ ] **Step 3: Remove stdio log buckets**

  Replace `_api_call_logs` with:

  ```python
  _api_call_logs: Dict[str, List[Dict[str, Any]]] = {
      "http": [],
  }
  ```

  Replace the URI summary loop with:

  ```python
  for prefix in ["http_", ""]:
      uri_file = os.path.join(_LOG_DIR, f"{prefix}uri.json")
      if os.path.exists(uri_file):
          all_files.append(f"{prefix}uri.json")
  ```

- [ ] **Step 4: Remove `call_tool_stdio`**

  Delete `call_tool_stdio()` and its stdio-specific comments. Keep `http_get()`, `http_post()`, `call_tool_http()`, `_call_proxy_only_tool_locally()`, and `_is_proxy_transport_error()` only if still used by HTTP-only tests.

- [ ] **Step 5: Make parametrization and `tool_caller` HTTP-only**

  Replace `pytest_generate_tests()` and `transport_mode()` with:

  ```python
  def pytest_generate_tests(metafunc):
      """HTTP is the only supported transport."""
      if "transport_mode" in metafunc.fixturenames:
          metafunc.parametrize("transport_mode", ["http"], scope="session")


  @pytest.fixture(scope="session")
  def transport_mode():
      """获取当前测试的传输模式。"""
      return "http"
  ```

  Replace `tool_caller()` with:

  ```python
  @pytest.fixture
  def tool_caller(instance_port):
      """返回 HTTP 工具调用函数。"""
      if not _is_http_proxy_available():
          pytest.skip("HTTP proxy not available")

      def caller(tool_name: str, params: Optional[dict] = None, **kwargs) -> Any:
          call_params = {**(params or {}), **kwargs}
          route_port = call_params.get("port")
          selected_port = route_port if isinstance(route_port, int) else instance_port
          return call_tool_http(tool_name, call_params, selected_port)

      return caller
  ```

- [ ] **Step 6: Update cached fixtures to use HTTP**

  Replace each `call_tool_stdio(...)` call in cached fixtures with `call_tool_http(...)`:

  ```python
  result = call_tool_http("get_metadata", {}, instance_port)
  result = call_tool_http("list_functions", {"offset": 0, "count": 100}, instance_port)
  result = call_tool_http("list_strings", {"offset": 0, "count": 100}, instance_port)
  result = call_tool_http("list_globals", {"offset": 0, "count": 1000}, instance_port)
  result = call_tool_http("get_entry_points", {}, instance_port)
  result = call_tool_http("list_local_types", {}, instance_port)
  ```

- [ ] **Step 7: Verify pytest rejects stdio and accepts HTTP**

  Run: `pytest --transport=stdio --collect-only`

  Expected: FAIL during argument parsing with `invalid choice: 'stdio'`.

  Run: `pytest --transport=http --collect-only`

  Expected: collection succeeds, with live-IDA dependent tests collected or skipped according to fixtures.

- [ ] **Step 8: Checkpoint without commit**

  Run: `git diff -- test/conftest.py test/test_lifecycle.py`

  Expected: test harness is HTTP-only and no `call_tool_stdio` remains. Do not commit unless the user explicitly requests it.

## Task 4: Convert live test runner to HTTP-only

**Files:**
- Modify: `test/test.py:20-33`, `test/test.py:137-162`, `test/test.py:176-178`

- [ ] **Step 1: Update runner usage text**

  Replace the transport usage block in `test/test.py` with:

  ```python
      # Transport mode:
      python test/test.py --transport=http     # Test HTTP mode (default)

      # Combined usage:
      python test/test.py --core --analysis    # Run core and analysis
      python test/test.py --transport=http --analysis  # Run analysis in HTTP mode

      # Direct pytest usage:
      pytest -m core                      # Run core module only
      pytest -m "core or analysis"        # Run core and analysis
      pytest -m "not debug"               # Exclude debug module
      pytest --transport=http             # Test HTTP mode
  ```

- [ ] **Step 2: Reject non-HTTP transport values**

  Replace transport parsing with:

  ```python
  transport_mode = "http"
  remaining_args: list[str] = []

  if args:
      for arg in args:
          if arg == "--all":
              run_all = True
          elif arg.startswith("--transport="):
              transport_mode = arg.split("=", 1)[1]
              if transport_mode != "http":
                  print("ERROR: only HTTP transport is supported. Use --transport=http.")
                  return 1
          elif arg.startswith("--") and arg[2:] in MODULES:
              selected_modules.append(arg[2:])
          else:
              remaining_args.append(arg)
  ```

- [ ] **Step 3: Simplify HTTP proxy check**

  Replace the conditional proxy check with:

  ```python
  if not check_http_proxy():
      print(f"WARNING: HTTP proxy not available at {GATEWAY_HOST}:{GATEWAY_PORT}")
      print("Please check config.conf and restart IDA plugin.")
      return 1
  ```

- [ ] **Step 4: Verify runner behavior**

  Run: `python test/test.py --transport=stdio --core`

  Expected: exit code 1 and output contains `only HTTP transport is supported`.

  Run: `python test/test.py --transport=http --help`

  Expected: exit code 0 and help shows only HTTP transport examples.

- [ ] **Step 5: Checkpoint without commit**

  Run: `git diff -- test/test.py`

  Expected: runner docs and parsing are HTTP-only. Do not commit unless the user explicitly requests it.

## Task 5: Update documentation and project maps

**Files:**
- Modify: `README.md:43-76`
- Modify: `project.md:5-7`
- Modify: `API.md:14-27`
- Modify: `roadmap.md`
- Modify: `ida_mcp/project.md:45-59`
- Modify: `ida_mcp/roadmap.md:42-47`, `ida_mcp/roadmap.md:110-119`

- [ ] **Step 1: Update repository and package maps**

  In `project.md`, keep responsibility wording HTTP-specific:

  ```markdown
  IDA-MCP is the standalone IDA Pro plugin and MCP gateway project. It owns IDA
  runtime integration, FastMCP tools/resources, direct instance HTTP MCP transport,
  gateway/proxy behavior, CLI control, and live-IDA integration tests.
  ```

  In `ida_mcp/project.md`, replace only the proxy tree comments that mention stdio or a nonexistent HTTP transport entrypoint. Keep `register_tools.py` and `lifecycle.py` in the tree. The proxy section should include:

  ```text
      ├── register_tools.py       # proxy 侧工具注册与包装
      ├── lifecycle.py            # open_in_ida / close / staging / path bridge
      ├── _http.py                # gateway/internal HTTP 请求辅助
      ├── _state.py               # 实例选择与路由状态
      ├── _server.py              # HTTP gateway proxy FastMCP server
  ```

  Replace `config.py` boundary text with:

  ```markdown
  - `config.py` 读取 HTTP、端口、路径、超时和 unsafe 策略。
  ```

- [ ] **Step 2: Update README test examples**

  Keep HTTP examples and remove any implication of dual transport. The tests section should include:

  ```markdown
  python test/test.py
  python test/test.py --core --analysis
  python test/test.py --transport=http --analysis

  pytest -m "core or analysis"
  pytest -m "not debug"
  pytest --transport=http
  ```

- [ ] **Step 3: Update API transport wording**

  In `API.md`, ensure the transport endpoint section says these are HTTP endpoints only. Keep `py_eval` `stdout`/`stderr` result fields unchanged because they are not transport support.

- [ ] **Step 4: Update roadmaps**

  In `ida_mcp/roadmap.md`, replace:

  ```markdown
  - `../test/` 保证 HTTP、多模块行为稳定。
  ```

  Replace the old transport matrix item with:

  ```markdown
  - 明确 HTTP gateway proxy 与 direct instance HTTP 的测试矩阵。
  ```

  Apply the same HTTP-only wording to root `roadmap.md` where transport support is described.

- [ ] **Step 5: Verify documentation grep**

  Run: `rg -n "stdio|HTTP/stdio|多 transport|transport matrix|两种模式" README.md API.md project.md roadmap.md ida_mcp/project.md ida_mcp/roadmap.md`

  Expected: no true stdio transport support references. Matches in the design/plan docs are acceptable only under `docs/superpowers`.

- [ ] **Step 6: Checkpoint without commit**

  Run: `git diff -- README.md API.md project.md roadmap.md ida_mcp/project.md ida_mcp/roadmap.md`

  Expected: docs describe only HTTP transport. Do not commit unless the user explicitly requests it.

## Task 6: Final verification and cleanup

**Files:**
- Validate: all modified files

- [ ] **Step 1: Search for true stdio support across source/tests/docs**

  Run: `rg -n "is_stdio_enabled|enable_stdio|ida_mcp_proxy|call_tool_stdio|transport=stdio|transport=both|stdio_" ida_mcp ida_mcp.py test README.md API.md project.md roadmap.md`

  Expected: no matches.

- [ ] **Step 2: Search incidental I/O separately**

  Run: `rg -n "stdin|stdout|stderr|stdio" ida_mcp install.py test/samples API.md`

  Expected: only incidental process I/O, `py_eval` output fields, or C sample headers remain. No MCP stdio transport support remains.

- [ ] **Step 3: Run focused non-live tests**

  Run: `pytest test/test_lifecycle.py test/test_server_factory.py -v`

  Expected: PASS for tests that do not require live IDA; live environment-dependent tests may skip.

- [ ] **Step 4: Run HTTP collection**

  Run: `pytest --transport=http --collect-only`

  Expected: collection succeeds.

- [ ] **Step 5: Run live HTTP suite if gateway and IDA are available**

  Run: `pytest --transport=http -m "not debug" -v`

  Expected when gateway and a live IDA instance are available: PASS or documented skips for unavailable live prerequisites.

- [ ] **Step 6: Inspect final diff**

  Run: `git status --short && git diff --stat && git diff --name-status`

  Expected: only planned source, test, docs, and superpowers spec/plan files changed; `ida_mcp/proxy/ida_mcp_proxy.py` deleted.

- [ ] **Step 7: Report results without committing**

  Summarize changed files and verification output. Do not commit unless the user explicitly requests it.

## Self-Review

- Spec coverage: config removal is covered by Task 1; proxy deletion by Task 2; HTTP-only tests by Tasks 3-4; docs by Task 5; final grep and validation by Task 6.
- Placeholder scan: no TBD/TODO/fill-in-later instructions are present.
- Type consistency: all named functions and files match the current repository inventory; `call_tool_http`, `is_http_enabled`, and pytest fixtures already exist before this plan starts.
