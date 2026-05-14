# IDA-MCP Repository Roadmap Index

仓库以 `ide/` 子项目为主体，`ida_mcp` 作为受管资源打包在 `ide/resources/` 中。
工具/API 契约文档随插件资源存放在 `ide/resources/ida_mcp/API.md`，根目录只保留仓库级入口文档。

## 子项目

### `ide/` — 主项目

PySide6 桌面 IDE，负责安装、配置、状态监控和 gateway 生命周期管理。

规划文档：`ide/roadmap.md`

### `ide/resources/ida_mcp/` — 受管资源

IDA 插件源码（`ida_mcp.py` + `ida_mcp/` 包）、API 契约文档和 live-IDA pytest 套件。安装时 IDE 只复制 `ida_mcp.py` 与 `ida_mcp/` 包到 IDA plugins 目录。包含 `command.py` CLI 和 `registry_server.py` gateway 服务器。

规划文档：`ide/resources/ida_mcp/ida_mcp/roadmap.md`

当前测试基线：

- 主体 API/资源/修改/建模测试以 `ide/resources/ida_mcp/test/samples/complex.exe` 为固定基准。
- lifecycle 打开与关闭流程使用 `ide/resources/ida_mcp/test/samples/simple.exe`，避免关闭主测试实例。
- `get_metadata` 以 IDA 9.x 的 `ida_ida` 元数据为准，x64 PE 应返回 `arch=x86_64`、`bits=64`、`endian=little`。

## 阅读顺序

1. `project.md` — 仓库级项目地图
2. `codemap.md` — 仓库边界、入口和调用链索引
3. `ide/project.md` + `ide/roadmap.md` — IDE 子项目结构与规划
4. `ide/resources/ida_mcp/API.md` — MCP 工具与响应契约
5. `README.md` — 用户文档
