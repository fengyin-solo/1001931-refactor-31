"""巡视单状态流转：列表页、接口层与服务层共用同一份规则结论。"""
from __future__ import annotations

from typing import Any

INITIAL_STATUS = "待派发"
INSPECTING_STATUS = "巡视中"
SUBMITTED_STATUS = "已提交"
VOID_STATUS = "已作废"

DISPATCH_ACTION = "派发巡视"
SUBMIT_ACTION = "提交结果"
VOID_ACTION = "作废巡视"

STATUS_ORDER = [
    INITIAL_STATUS,
    INSPECTING_STATUS,
    SUBMITTED_STATUS,
    VOID_STATUS,
]
ACTIONS = [DISPATCH_ACTION, SUBMIT_ACTION, VOID_ACTION]
NEGATIVE_ACTIONS = (VOID_ACTION,)

# 只列出当前状态允许执行的动作；已作废没有任何后继动作，因此不会被推回巡视中。
TRANSITIONS: dict[str, dict[str, str]] = {
    INITIAL_STATUS: {
        DISPATCH_ACTION: INSPECTING_STATUS,
        VOID_ACTION: VOID_STATUS,
    },
    INSPECTING_STATUS: {
        SUBMIT_ACTION: SUBMITTED_STATUS,
        VOID_ACTION: VOID_STATUS,
    },
    SUBMITTED_STATUS: {
        VOID_ACTION: VOID_STATUS,
    },
    VOID_STATUS: {},
}

# 作废后的复位口径也集中在这里，避免调用方各自按状态序号推断。
STATUS_FLAGS: dict[str, dict[str, bool]] = {
    INITIAL_STATUS: {"pending": True, "abnormal": False},
    INSPECTING_STATUS: {"pending": True, "abnormal": False},
    SUBMITTED_STATUS: {"pending": False, "abnormal": False},
    VOID_STATUS: {"pending": False, "abnormal": True},
}

# 保持历史接口中“动作 -> 目标状态”的扁平表；实际能否执行由 TRANSITIONS 按当前状态判定。
ACTION_RULES = {
    DISPATCH_ACTION: INSPECTING_STATUS,
    SUBMIT_ACTION: SUBMITTED_STATUS,
    VOID_ACTION: VOID_STATUS,
}


def allowed_actions(status: Any) -> list[str]:
    """按状态返回保持动作顺序的可执行清单。"""
    rules = TRANSITIONS.get(str(status), {})
    return [action for action in ACTIONS if action in rules]


def target_status(status: Any, action: str) -> str | None:
    """返回动作的目标状态；当前状态不允许该动作时返回 None。"""
    return TRANSITIONS.get(str(status), {}).get(action)


def reject_reason(status: Any, action: str) -> str | None:
    """返回不能执行动作的原因；允许执行时返回 None。"""
    if action not in ACTIONS:
        return f"动作「{action}」不属于巡视检查可执行范围"

    current_status = str(status)
    if current_status not in TRANSITIONS:
        return f"巡视单当前状态「{current_status}」不在允许的状态序列里"
    if action not in TRANSITIONS[current_status]:
        if current_status == VOID_STATUS:
            return "已作废的巡视单不能再推进，请重新登记巡视单"
        return f"巡视单当前为{current_status}，不能执行{action}"
    return None


def apply_action(entry: dict[str, Any], action: str) -> str | None:
    """按共用规则改写巡视单；只改状态与汇总标记，业务历史字段原样保留。"""
    current_status = entry.get("status", INITIAL_STATUS)
    target = target_status(current_status, action)
    if target is None:
        return reject_reason(current_status, action)

    entry["status"] = target
    entry["pending"] = STATUS_FLAGS[target]["pending"]
    entry["abnormal"] = STATUS_FLAGS[target]["abnormal"]
    return None


def present_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """统一列表与详情读到的进度，同时不改动巡视路线、发现问题数等历史字段。"""
    item = dict(entry)
    item["巡视状态"] = item.get("status")
    return item


def workflow_rules() -> dict[str, Any]:
    """给前端页面返回同一份状态顺序、允许动作、作废负向规则和复位标记。"""
    return {
        "status_order": STATUS_ORDER,
        "initial_status": INITIAL_STATUS,
        "actions": ACTIONS,
        "negative_actions": list(NEGATIVE_ACTIONS),
        "transitions": {
            status: dict(action_rules)
            for status, action_rules in TRANSITIONS.items()
        },
        "status_flags": {
            status: dict(flags)
            for status, flags in STATUS_FLAGS.items()
        },
    }
