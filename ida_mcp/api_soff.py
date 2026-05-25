"""Soff API - Binary diffing via direct SQLite access.

Provides tools:
    - soff_export        Export current IDB to soff SQLite database (requires IDA)
    - soff_diff_results  Get diff match/unmatched list from .soff result file
    - soff_diff_asm      Unified diff of two functions' assembly
    - soff_diff_pseudo   Unified diff of two functions' pseudocode
"""
from __future__ import annotations

import os
import sqlite3
from difflib import unified_diff
from typing import Annotated, List, Union

from .rpc import tool
from .sync import idawrite
from .utils import parse_address

try:
    import idc  # type: ignore
    import idaapi  # type: ignore
except ImportError:
    pass


def _addr_to_str(value: Union[int, str]) -> str:
    """Parse address to decimal string."""
    result = parse_address(value)
    if not result["ok"]:
        raise ValueError(f"invalid address: {value}")
    return str(result["value"])


def _query_column(db_path: str, address: str, column: str) -> str:
    """Query a single column from functions table by address."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            f"SELECT {column} FROM functions WHERE address = ? LIMIT 1",
            (address,),
        ).fetchone()
        return row[0] if row and row[0] else ""
    finally:
        conn.close()


def _compute_unified_diff(left_text: str, right_text: str) -> str:
    """Compute unified diff between two texts."""
    left_lines = left_text.splitlines(keepends=True)
    right_lines = right_text.splitlines(keepends=True)
    result = []
    for line in unified_diff(left_lines, right_lines, lineterm=""):
        # Skip --- +++ @@ headers
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        result.append(line)
    return "".join(result) if result else " (identical)\n"


@tool
@idawrite
def soff_export(
    output_path: Annotated[str, "Output SQLite path. If empty, uses IDB path with .sqlite extension."] = "",
) -> dict:
    """Export current IDB to soff SQLite database for binary diffing. Requires IDA."""
    if not output_path:
        idb = idaapi.get_path(idaapi.PATH_TYPE_IDB)
        output_path = os.path.splitext(idb)[0] + ".sqlite"
    output_path = output_path.replace("\\", "\\\\")
    import json
    result_str = idc.eval_idc(f'soff_export("{output_path}")')
    if result_str is None or result_str == "":
        return {"error": "soff plugin not loaded or IDC function not available"}
    return json.loads(result_str)


@tool
def soff_diff_results(
    result_path: Annotated[str, "Path to .soff result file"],
    match_type: Annotated[str, "Filter: 'all', 'best', 'partial', 'unreliable', or 'unmatched'"] = "all",
    limit: Annotated[int, "Max rows to return"] = 100,
    offset: Annotated[int, "Skip first N rows"] = 0,
) -> dict:
    """Get diff results (matches and unmatched functions) from a .soff file."""
    if not os.path.exists(result_path):
        return {"error": f"file not found: {result_path}"}

    conn = sqlite3.connect(result_path)
    try:
        # Read config
        cfg = conn.execute("SELECT main_db, diff_db FROM config LIMIT 1").fetchone()
        main_db = cfg[0] if cfg else ""
        diff_db = cfg[1] if cfg else ""

        if match_type == "unmatched":
            rows = conn.execute(
                "SELECT type, address, name FROM unmatched ORDER BY line LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total = conn.execute("SELECT count(*) FROM unmatched").fetchone()[0]
            items = [{"side": r[0], "address": r[1], "name": r[2]} for r in rows]
        else:
            where = "" if match_type == "all" else f"WHERE type = '{match_type}'"
            rows = conn.execute(
                f"SELECT type, address, name, address2, name2, ratio, description "
                f"FROM results {where} ORDER BY line LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total = conn.execute(f"SELECT count(*) FROM results {where}").fetchone()[0]
            items = [
                {
                    "type": r[0],
                    "primary_addr": r[1], "primary_name": r[2],
                    "secondary_addr": r[3], "secondary_name": r[4],
                    "ratio": r[5], "description": r[6],
                }
                for r in rows
            ]

        return {
            "main_db": main_db,
            "diff_db": diff_db,
            "total": total,
            "offset": offset,
            "count": len(items),
            "items": items,
        }
    finally:
        conn.close()


@tool
def soff_diff_asm(
    main_db: Annotated[str, "Path to primary exported SQLite"],
    diff_db: Annotated[str, "Path to secondary exported SQLite"],
    primary_addr: Annotated[Union[int, str], "Primary function address (hex or decimal)"],
    secondary_addr: Annotated[Union[int, str], "Secondary function address (hex or decimal)"],
) -> str:
    """Diff assembly of two functions. Returns unified diff text (+/-)."""
    p_addr = _addr_to_str(primary_addr)
    s_addr = _addr_to_str(secondary_addr)
    left = _query_column(main_db, p_addr, "assembly")
    right = _query_column(diff_db, s_addr, "assembly")
    if not left and not right:
        return "error: functions not found in databases"
    return _compute_unified_diff(left, right)


@tool
def soff_diff_pseudo(
    main_db: Annotated[str, "Path to primary exported SQLite"],
    diff_db: Annotated[str, "Path to secondary exported SQLite"],
    primary_addr: Annotated[Union[int, str], "Primary function address (hex or decimal)"],
    secondary_addr: Annotated[Union[int, str], "Secondary function address (hex or decimal)"],
) -> str:
    """Diff pseudocode of two functions. Returns unified diff text (+/-)."""
    p_addr = _addr_to_str(primary_addr)
    s_addr = _addr_to_str(secondary_addr)
    left = _query_column(main_db, p_addr, "pseudocode")
    right = _query_column(diff_db, s_addr, "pseudocode")
    if not left and not right:
        return "error: functions not found in databases"
    return _compute_unified_diff(left, right)
