"""巡视检查业务规则：字段校验、筛选口径与共用状态流转。"""
from __future__ import annotations

import threading
from typing import Any

from app import patrol_workflow as workflow
from app.store import store

MODULE = "patrol"
REQUIRED_FIELDS = ["巡视单号", "巡视路线", "巡视人员"]
STATUS_ORDER = workflow.STATUS_ORDER
ACTION_RULES = workflow.ACTION_RULES
NEGATIVE_ACTIONS = list(workflow.NEGATIVE_ACTIONS)
_action_lock = threading.Lock()


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
        page_rows = rows[start:start + size]
        return [workflow.present_entry(row) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return workflow.present_entry(entry)

    def workflow_rules(self) -> dict[str, Any]:
        return workflow.workflow_rules()

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = workflow.INITIAL_STATUS
        entry["pending"] = workflow.STATUS_FLAGS[workflow.INITIAL_STATUS]["pending"]
        entry["abnormal"] = workflow.STATUS_FLAGS[workflow.INITIAL_STATUS]["abnormal"]
        rows.append(entry)
        return workflow.present_entry(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        with _action_lock:
            entry = store.find(MODULE, entry_id)
            if entry is None:
                return None, f"巡视单 {entry_id} 不存在或已归档"

            error = workflow.apply_action(entry, action)
            if error is not None:
                return None, error
            return workflow.present_entry(entry), f"巡视单已{action}"
