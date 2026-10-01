"""巡视单推进规则：顺序表、允许动作与作废复位规则的唯一出处。

路由层、服务层与巡视列表页都从这里取结论，避免各写一份导致进度不一致：

- STATUS_ORDER 是巡视单的推进顺序：待派发 → 巡视中 → 已提交，已作废为终态；
- ALLOWED_ACTIONS 给出每个状态下还允许执行的动作，已作废不能再被推回巡视中，
  已提交后重复提交只认第一次；
- 作废是负向动作，与提交结果冲突时以作废为准，作废后只复位进度字段，
  历史巡视路线与发现问题数原样保留。
"""
from __future__ import annotations

from typing import Any

STATUS_ORDER = ["待派发", "巡视中", "已提交", "已作废"]
ACTION_RULES = {"派发巡视": "巡视中", "提交结果": "已提交", "作废巡视": "已作废"}
NEGATIVE_ACTIONS = ["作废巡视"]

VOID_STATUS = STATUS_ORDER[-1]  # 已作废：作废复位后的终态
SUBMITTED_STATUS = STATUS_ORDER[2]  # 已提交：提交结果只走一次
DISPATCH_ACTION = "派发巡视"
SUBMIT_ACTION = "提交结果"

# 每个状态允许执行的动作：作废在任何非终态都可用，作废与提交冲突时以作废为准。
ALLOWED_ACTIONS = {
    "待派发": ["派发巡视", "作废巡视"],
    "巡视中": ["提交结果", "作废巡视"],
    "已提交": ["作废巡视"],
    "已作废": [],
}


def allowed_actions(status: str) -> list[str]:
    """按状态给出当前可执行的动作；未知状态不给任何动作。"""
    return list(ALLOWED_ACTIONS.get(status, []))


def check_action(status: str, action: str) -> str | None:
    """校验动作能否在当前状态执行；返回 None 表示允许，否则是给用户看的原因。"""
    if action not in ACTION_RULES:
        return f"动作「{action}」不属于巡视检查可执行范围"
    if action in allowed_actions(status):
        return None
    if status == VOID_STATUS and action == DISPATCH_ACTION:
        return "巡视单已作废，不能再推回巡视中"
    if status == VOID_STATUS:
        return f"巡视单已作废，以作废为准，不再执行「{action}」"
    if action == SUBMIT_ACTION and status == SUBMITTED_STATUS:
        return "巡视单已提交，请勿重复提交"
    return f"当前状态「{status}」不允许执行「{action}」"


def apply_action(entry: dict[str, Any], action: str) -> dict[str, Any]:
    """按动作推进巡视单：只改写进度字段，历史巡视路线与发现问题数原样保留。"""
    target = ACTION_RULES[action]
    entry["status"] = target
    entry["pending"] = target != VOID_STATUS
    entry["abnormal"] = action in NEGATIVE_ACTIONS
    return entry
