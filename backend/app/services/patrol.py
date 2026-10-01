"""巡视检查业务规则：状态流转、字段校验与筛选口径都收在这里。

巡视单的推进顺序、允许动作与作废复位规则统一来自 patrol_flow，
路由层与巡视列表页读到的都是同一份结论。
"""
from __future__ import annotations

from typing import Any

from app.services.patrol_flow import (
    STATUS_ORDER,
    allowed_actions,
    apply_action,
    check_action,
)
from app.store import store

MODULE = "patrol"
REQUIRED_FIELDS = ["巡视单号", "巡视路线", "巡视人员"]


def with_allowed_actions(row: dict[str, Any]) -> dict[str, Any]:
    """给列表与详情挂上当前状态允许的动作，各端按同一份结论展示。"""
    return {**row, "allowed_actions": allowed_actions(str(row.get("status") or ""))}


class PatrolService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("巡视单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return [with_allowed_actions(row) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return with_allowed_actions(entry)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return with_allowed_actions(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"巡视单 {entry_id} 不存在或已归档"
        reason = check_action(str(entry.get("status") or ""), action)
        if reason is not None:
            return None, reason
        apply_action(entry, action)
        return with_allowed_actions(entry), f"巡视单已{action}"
