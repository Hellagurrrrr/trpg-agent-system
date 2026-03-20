"""
世界状态（单一真相源）与状态应用逻辑。
v0.0 原则：除本模块与 Rules 产生的 mechanical_effects 外，不让 LLM 直接改结构化字段。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from schemas import ParsedAction


# 效果类型常量（与 rules_engine 中构造的 mechanical_effects 保持一致）
def _clamp_int(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _resolve_container(state: MutableMapping[str, Any], path: str) -> Tuple[MutableMapping[str, Any], str]:
    parts = path.split(".")
    cur: Any = state
    for p in parts[:-1]:
        cur = cur[p]
    return cur, parts[-1]


def apply_mechanical_effects(state: MutableMapping[str, Any], effects: List[Mapping[str, Any]]) -> None:
    """
    将 Rules 产出的结构化效果应用到 state。
    每种 type 约定不同字段；未知类型忽略（便于后续扩展）。
    """
    for eff in effects:
        t = eff.get("type")
        if t == "location_change":
            state["world"]["current_location"] = eff["value"]
        elif t == "location_unlock":
            loc = eff["value"]
            ul = state["world"].setdefault("unlocked_locations", [])
            if loc not in ul:
                ul.append(loc)
        elif t == "npc_alert_change":
            nid = eff["target"]
            delta = int(eff["delta"])
            npc = state["npcs"].setdefault(nid, {})
            base = int(npc.get("alert_level", 0))
            npc["alert_level"] = _clamp_int(base + delta, 0, 5)
        elif t == "clue_add":
            clue = eff["value"]
            dc = state["world"].setdefault("discovered_clues", [])
            if clue not in dc:
                dc.append(clue)
        elif t == "hp_change":
            delta = int(eff["delta"])
            p = state["player"]
            p["hp"] = _clamp_int(int(p.get("hp", 0)) + delta, 0, 999)
        elif t == "inventory_add":
            item = eff["value"]
            inv = state["player"].setdefault("inventory", [])
            if item not in inv:
                inv.append(item)
        elif t == "quest_status":
            # eff: target_path 如 quests.main_quest.status, value
            path = eff["path"]
            container, key = _resolve_container(state, path)
            container[key] = eff["value"]
        elif t == "history_append":
            msg = eff["value"]
            state.setdefault("history", {}).setdefault("recent_turns", []).append(msg)


def init_world_state(session_id: Optional[str] = None, player_name: str = "玩家") -> Dict[str, Any]:
    """
    庄园调查案模组初始状态（README WorldState 最小版）。
    属性数值固定，符合 v0.0「初始数值固定」。
    """
    sid = session_id or f"session_{uuid.uuid4().hex[:8]}"
    return {
        "session_id": sid,
        "module_id": "manor_mystery_v0",
        "turn_id": 0,
        "player": {
            "name": player_name,
            "hp": 10,
            "attributes": {
                "strength": 1,
                "agility": 2,
                "intelligence": 2,
                "charisma": 2,
            },
            "inventory": [],
            "status_flags": [],
        },
        "world": {
            "current_location": "庄园门口",
            "time_stage": "傍晚",
            "discovered_clues": [],
            "unlocked_locations": ["庄园门口"],
            "chapter": "chapter_1",
        },
        "npcs": {
            "guard": {
                "state": "值守中",
                "alert_level": 2,
                "attitude": "中立",
            }
        },
        "quests": {
            "main_quest": {
                "id": "enter_manor",
                "description": "进入庄园并寻找账本",
                "status": "in_progress",
            }
        },
        "history": {
            "recent_turns": [f"{player_name}来到庄园门口，主线：进入庄园并寻找账本。"],
        },
    }


def apply_no_check_updates(state: MutableMapping[str, Any], parsed: ParsedAction) -> None:
    """
    无需检定的动作：仅由 WorldState 做最小、可预测更新（PM 已判定 requires_check=False）。
    observe / talk / move 等走此路径。
    """
    loc = state["world"]["current_location"]
    ul = set(state["world"].get("unlocked_locations") or [])
    hist = state.setdefault("history", {}).setdefault("recent_turns", [])

    if parsed.action_type == "observe":
        hist.append(f"{state['player']['name']}观察了周围环境（{loc}）。")
        return

    if parsed.action_type == "talk":
        tgt = parsed.target or "对方"
        hist.append(f"{state['player']['name']}与{tgt}交谈。")
        return

    if parsed.action_type == "move":
        # 目标地点须在已解锁列表中，避免 LLM 口述即瞬移
        dest = (parsed.target or "").strip()
        if dest and dest in ul:
            state["world"]["current_location"] = dest
            hist.append(f"{state['player']['name']}前往{dest}。")
        else:
            hist.append(f"{state['player']['name']}尝试移动，但目标未解锁或不明：{dest or '（未指定）'}。")
        return

    if parsed.action_type == "take_item":
        item = (parsed.target or parsed.method or "物品").strip()
        if item:
            inv = state["player"].setdefault("inventory", [])
            if item not in inv:
                inv.append(item)
            hist.append(f"{state['player']['name']}拿取了{item}。")
        return

    # 其他无检类型：打日志即可，避免静默丢输入
    hist.append(
        f"{state['player']['name']}行动（{parsed.action_type}），当前地点 {loc}。"
    )


def apply_result(
    state: MutableMapping[str, Any], parsed_action: ParsedAction, rule_result: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    回合结束时的状态归并入口。
    - 有检定：先应用 mechanical_effects，再视情况补充 history
    - 无检定：走 apply_no_check_updates
    """
    outcome = rule_result.get("outcome", "none")
    effects = list(rule_result.get("mechanical_effects") or [])

    if parsed_action.requires_check and outcome != "none":
        apply_mechanical_effects(state, effects)
        # 主线：成功进入庄园外院则更新任务状态
        if state["world"]["current_location"] == "庄园外院":
            mq = state["quests"]["main_quest"]
            if mq.get("status") == "in_progress" and mq.get("id") == "enter_manor":
                mq["status"] = "entered_manor"
                state.setdefault("history", {}).setdefault("recent_turns", []).append(
                    "主线进度更新：已进入庄园，可继续寻找账本。"
                )
    else:
        apply_no_check_updates(state, parsed_action)

    return state
